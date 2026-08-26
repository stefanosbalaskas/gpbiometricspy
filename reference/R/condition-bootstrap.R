
# Bootstrap condition-comparison helper.

.gp_boot_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }
  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }
  invisible(data)
}

.gp_boot_check_cols <- function(data, cols) {
  cols <- cols[!is.na(cols) & nzchar(cols)]
  missing <- setdiff(cols, names(data))
  if (length(missing)) {
    stop("Missing columns: ", paste(missing, collapse = ", "), call. = FALSE)
  }
  invisible(TRUE)
}

.gp_boot_levels <- function(condition, condition_levels = NULL) {
  condition <- as.character(condition)

  if (!is.null(condition_levels)) {
    condition_levels <- as.character(condition_levels)
    if (length(condition_levels) != 2L) {
      stop("`condition_levels` must contain exactly two values.", call. = FALSE)
    }
    return(condition_levels)
  }

  levels <- unique(condition[!is.na(condition) & nzchar(condition)])

  if (length(levels) != 2L) {
    stop(
      "`condition_col` must contain exactly two non-missing conditions, ",
      "or supply `condition_levels`.",
      call. = FALSE
    )
  }

  levels
}

.gp_boot_group_indices <- function(data, by_cols = NULL) {
  if (is.null(by_cols) || !length(by_cols)) {
    return(list(all = seq_len(nrow(data))))
  }

  .gp_boot_check_cols(data, by_cols)
  split(seq_len(nrow(data)), interaction(data[by_cols], drop = TRUE, sep = " | "))
}

.gp_boot_bind_rows <- function(rows) {
  rows <- rows[!vapply(rows, is.null, logical(1))]

  if (!length(rows)) {
    return(data.frame())
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL
  out
}

.gp_boot_subject_condition_means <- function(data,
                                             outcome_col,
                                             condition_col,
                                             participant_col) {
  .gp_boot_check_cols(data, c(outcome_col, condition_col, participant_col))

  y <- suppressWarnings(as.numeric(data[[outcome_col]]))
  condition <- as.character(data[[condition_col]])
  participant <- as.character(data[[participant_col]])

  ok <- is.finite(y) & !is.na(condition) & nzchar(condition) &
    !is.na(participant) & nzchar(participant)

  data <- data[ok, , drop = FALSE]
  y <- y[ok]
  condition <- condition[ok]
  participant <- participant[ok]

  if (!length(y)) {
    return(data.frame(
      participant = character(),
      condition = character(),
      value = numeric()
    ))
  }

  key <- interaction(participant, condition, drop = TRUE, sep = " | ")
  groups <- split(seq_along(y), key)

  rows <- vector("list", length(groups))
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    k <- k + 1L
    rows[[k]] <- data.frame(
      participant = participant[idx[1L]],
      condition = condition[idx[1L]],
      value = mean(y[idx], na.rm = TRUE),
      n_observations = length(idx),
      stringsAsFactors = FALSE
    )
  }

  .gp_boot_bind_rows(rows)
}

.gp_boot_pooled_sd <- function(x1, x2) {
  x1 <- x1[is.finite(x1)]
  x2 <- x2[is.finite(x2)]

  if (length(x1) < 2L || length(x2) < 2L) {
    return(NA_real_)
  }

  s1 <- stats::var(x1, na.rm = TRUE)
  s2 <- stats::var(x2, na.rm = TRUE)

  denom <- length(x1) + length(x2) - 2L

  if (!is.finite(s1) || !is.finite(s2) || denom <= 0) {
    return(NA_real_)
  }

  sqrt(((length(x1) - 1L) * s1 + (length(x2) - 1L) * s2) / denom)
}

.gp_boot_effect <- function(x1,
                            x2,
                            statistic = c("mean_difference", "median_difference", "standardized_mean_difference"),
                            paired = FALSE) {
  statistic <- match.arg(statistic)

  x1 <- suppressWarnings(as.numeric(x1))
  x2 <- suppressWarnings(as.numeric(x2))

  if (isTRUE(paired)) {
    ok <- is.finite(x1) & is.finite(x2)
    x1 <- x1[ok]
    x2 <- x2[ok]
  } else {
    x1 <- x1[is.finite(x1)]
    x2 <- x2[is.finite(x2)]
  }

  if (!length(x1) || !length(x2)) {
    return(NA_real_)
  }

  if (statistic == "mean_difference") {
    return(mean(x2, na.rm = TRUE) - mean(x1, na.rm = TRUE))
  }

  if (statistic == "median_difference") {
    return(stats::median(x2, na.rm = TRUE) - stats::median(x1, na.rm = TRUE))
  }

  if (isTRUE(paired)) {
    d <- x2 - x1
    sd_d <- stats::sd(d, na.rm = TRUE)

    if (!is.finite(sd_d) || sd_d <= 0) {
      return(NA_real_)
    }

    return(mean(d, na.rm = TRUE) / sd_d)
  }

  pooled <- .gp_boot_pooled_sd(x1, x2)

  if (!is.finite(pooled) || pooled <= 0) {
    return(NA_real_)
  }

  (mean(x2, na.rm = TRUE) - mean(x1, na.rm = TRUE)) / pooled
}

.gp_boot_prepare_values <- function(data,
                                    outcome_col,
                                    condition_col,
                                    participant_col = NULL,
                                    condition_levels = NULL,
                                    paired = FALSE,
                                    na_rm = TRUE) {
  .gp_boot_check_cols(data, c(outcome_col, condition_col, participant_col))

  work <- data
  work$.outcome <- suppressWarnings(as.numeric(work[[outcome_col]]))
  work$.condition <- as.character(work[[condition_col]])

  if (isTRUE(na_rm)) {
    keep <- is.finite(work$.outcome) &
      !is.na(work$.condition) &
      nzchar(work$.condition)
    work <- work[keep, , drop = FALSE]
  }

  levels <- .gp_boot_levels(work$.condition, condition_levels)

  if (isTRUE(paired)) {
    if (is.null(participant_col)) {
      stop("`participant_col` is required when `paired = TRUE`.", call. = FALSE)
    }

    ag <- .gp_boot_subject_condition_means(
      work,
      outcome_col = outcome_col,
      condition_col = condition_col,
      participant_col = participant_col
    )

    ag <- ag[ag$condition %in% levels, , drop = FALSE]

    c1 <- ag[ag$condition == levels[1L], c("participant", "value"), drop = FALSE]
    c2 <- ag[ag$condition == levels[2L], c("participant", "value"), drop = FALSE]

    names(c1)[2L] <- "value_1"
    names(c2)[2L] <- "value_2"

    wide <- merge(c1, c2, by = "participant")

    return(list(
      condition_1 = levels[1L],
      condition_2 = levels[2L],
      x1 = wide$value_1,
      x2 = wide$value_2,
      participant = wide$participant,
      n_condition_1 = nrow(c1),
      n_condition_2 = nrow(c2),
      n_pairs = nrow(wide),
      unit_level = "participant_condition_mean"
    ))
  }

  if (!is.null(participant_col)) {
    ag <- .gp_boot_subject_condition_means(
      work,
      outcome_col = outcome_col,
      condition_col = condition_col,
      participant_col = participant_col
    )

    ag <- ag[ag$condition %in% levels, , drop = FALSE]

    return(list(
      condition_1 = levels[1L],
      condition_2 = levels[2L],
      x1 = ag$value[ag$condition == levels[1L]],
      x2 = ag$value[ag$condition == levels[2L]],
      participant = NULL,
      n_condition_1 = sum(ag$condition == levels[1L]),
      n_condition_2 = sum(ag$condition == levels[2L]),
      n_pairs = NA_integer_,
      unit_level = "participant_condition_mean"
    ))
  }

  work <- work[work$.condition %in% levels, , drop = FALSE]

  list(
    condition_1 = levels[1L],
    condition_2 = levels[2L],
    x1 = work$.outcome[work$.condition == levels[1L]],
    x2 = work$.outcome[work$.condition == levels[2L]],
    participant = NULL,
    n_condition_1 = sum(work$.condition == levels[1L]),
    n_condition_2 = sum(work$.condition == levels[2L]),
    n_pairs = NA_integer_,
    unit_level = "row"
  )
}

.gp_boot_once <- function(x1, x2, statistic, paired) {
  if (isTRUE(paired)) {
    n <- length(x1)
    if (n < 1L) {
      return(NA_real_)
    }
    idx <- sample.int(n, size = n, replace = TRUE)
    return(.gp_boot_effect(x1[idx], x2[idx], statistic = statistic, paired = TRUE))
  }

  if (!length(x1) || !length(x2)) {
    return(NA_real_)
  }

  b1 <- sample(x1, size = length(x1), replace = TRUE)
  b2 <- sample(x2, size = length(x2), replace = TRUE)

  .gp_boot_effect(b1, b2, statistic = statistic, paired = FALSE)
}

.gp_boot_compare_one <- function(data,
                                 outcome_col,
                                 condition_col,
                                 participant_col = NULL,
                                 condition_levels = NULL,
                                 paired = FALSE,
                                 statistic = "mean_difference",
                                 n_boot = 2000,
                                 conf_level = 0.95,
                                 seed = NULL,
                                 na_rm = TRUE) {
  vals <- .gp_boot_prepare_values(
    data = data,
    outcome_col = outcome_col,
    condition_col = condition_col,
    participant_col = participant_col,
    condition_levels = condition_levels,
    paired = paired,
    na_rm = na_rm
  )

  estimate <- .gp_boot_effect(
    vals$x1,
    vals$x2,
    statistic = statistic,
    paired = paired
  )

  if (!is.null(seed)) {
    old_seed <- if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
      get(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    } else {
      NULL
    }

    set.seed(seed)

    on.exit({
      if (is.null(old_seed)) {
        if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
          rm(".Random.seed", envir = .GlobalEnv)
        }
      } else {
        assign(".Random.seed", old_seed, envir = .GlobalEnv)
      }
    }, add = TRUE)
  }

  boot <- replicate(
    n_boot,
    .gp_boot_once(vals$x1, vals$x2, statistic = statistic, paired = paired)
  )

  boot_finite <- boot[is.finite(boot)]

  alpha <- 1 - conf_level

  ci <- if (length(boot_finite)) {
    as.numeric(stats::quantile(
      boot_finite,
      probs = c(alpha / 2, 1 - alpha / 2),
      na.rm = TRUE,
      names = FALSE,
      type = 6
    ))
  } else {
    c(NA_real_, NA_real_)
  }

  p_boot <- if (length(boot_finite)) {
    p <- 2 * min(
      mean(boot_finite <= 0, na.rm = TRUE),
      mean(boot_finite >= 0, na.rm = TRUE)
    )
    min(1, max(0, p))
  } else {
    NA_real_
  }

  out <- data.frame(
    condition_1 = vals$condition_1,
    condition_2 = vals$condition_2,
    contrast = paste0(vals$condition_2, " - ", vals$condition_1),
    statistic = statistic,
    estimate = estimate,
    ci_low = ci[1L],
    ci_high = ci[2L],
    conf_level = conf_level,
    p_boot_two_sided = p_boot,
    n_boot = n_boot,
    n_valid_boot = length(boot_finite),
    paired = paired,
    unit_level = vals$unit_level,
    n_condition_1 = vals$n_condition_1,
    n_condition_2 = vals$n_condition_2,
    n_pairs = vals$n_pairs,
    stringsAsFactors = FALSE
  )

  attr(out, "bootstrap_samples") <- boot
  out
}

#' Bootstrap condition comparisons for Gazepoint-derived outcomes
#'
#' Compares two conditions using a transparent percentile bootstrap. The helper
#' is intended for trial-level, participant-level, or event-locked summaries
#' produced by `gpbiometrics`. When `participant_col` is supplied, observations
#' are first averaged at the participant-by-condition level to reduce
#' pseudo-replication. When `paired = TRUE`, only participants with both
#' conditions are retained and resampled as paired units.
#'
#' @param data Data frame containing the outcome and condition columns.
#' @param outcome_col Numeric outcome column.
#' @param condition_col Two-level condition column.
#' @param participant_col Optional participant/unit identifier. If supplied,
#'   the bootstrap uses participant-by-condition means.
#' @param condition_levels Optional two-element character vector defining the
#'   reference and target condition. The estimate is `condition_levels[2] -
#'   condition_levels[1]`.
#' @param paired If TRUE, perform a paired participant-level bootstrap. Requires
#'   `participant_col`.
#' @param by_cols Optional columns used to run separate comparisons by subgroup.
#' @param statistic Statistic to bootstrap: `"mean_difference"`,
#'   `"median_difference"`, or `"standardized_mean_difference"`.
#' @param n_boot Number of bootstrap resamples.
#' @param conf_level Confidence level for percentile intervals.
#' @param seed Optional random seed.
#' @param na_rm If TRUE, remove rows with missing/non-finite outcomes or missing
#'   condition labels.
#'
#' @return Object of class `gazepoint_bootstrap_condition_comparison`, stored as
#'   a data frame. Bootstrap samples are stored in the `bootstrap_samples`
#'   attribute.
#' @export
compare_gazepoint_conditions_bootstrap <- function(data,
                                                   outcome_col,
                                                   condition_col,
                                                   participant_col = NULL,
                                                   condition_levels = NULL,
                                                   paired = FALSE,
                                                   by_cols = NULL,
                                                   statistic = c("mean_difference", "median_difference", "standardized_mean_difference"),
                                                   n_boot = 2000,
                                                   conf_level = 0.95,
                                                   seed = NULL,
                                                   na_rm = TRUE) {
  statistic <- match.arg(statistic)

  .gp_boot_check_df(data)
  .gp_boot_check_cols(data, c(outcome_col, condition_col, participant_col, by_cols))

  if (!is.numeric(n_boot) || length(n_boot) != 1L || !is.finite(n_boot) || n_boot < 1) {
    stop("`n_boot` must be a positive integer.", call. = FALSE)
  }

  n_boot <- as.integer(n_boot)

  if (!is.numeric(conf_level) || length(conf_level) != 1L ||
    !is.finite(conf_level) || conf_level <= 0 || conf_level >= 1) {
    stop("`conf_level` must be between 0 and 1.", call. = FALSE)
  }

  if (isTRUE(paired) && is.null(participant_col)) {
    stop("`participant_col` is required when `paired = TRUE`.", call. = FALSE)
  }

  groups <- .gp_boot_group_indices(data, by_cols)
  rows <- list()
  boot_list <- list()
  k <- 0L

  for (g in names(groups)) {
    idx <- groups[[g]]
    z <- data[idx, , drop = FALSE]

    result <- .gp_boot_compare_one(
      data = z,
      outcome_col = outcome_col,
      condition_col = condition_col,
      participant_col = participant_col,
      condition_levels = condition_levels,
      paired = paired,
      statistic = statistic,
      n_boot = n_boot,
      conf_level = conf_level,
      seed = seed,
      na_rm = na_rm
    )

    boot <- attr(result, "bootstrap_samples")
    attr(result, "bootstrap_samples") <- NULL

    if (!is.null(by_cols) && length(by_cols)) {
      result <- cbind(z[1L, by_cols, drop = FALSE], result)
      boot_list[[g]] <- boot
    } else {
      boot_list[["all"]] <- boot
    }

    k <- k + 1L
    rows[[k]] <- result
  }

  out <- .gp_boot_bind_rows(rows)
  class(out) <- c("gazepoint_bootstrap_condition_comparison", "data.frame")
  attr(out, "bootstrap_samples") <- boot_list
  attr(out, "settings") <- list(
    outcome_col = outcome_col,
    condition_col = condition_col,
    participant_col = participant_col,
    condition_levels = condition_levels,
    paired = paired,
    by_cols = by_cols,
    statistic = statistic,
    n_boot = n_boot,
    conf_level = conf_level,
    seed = seed,
    na_rm = na_rm
  )

  out
}

