utils::globalVariables(c("time", "mean", "condition", "se"))

#' Prepare Gazepoint time-course data for cluster permutation testing
#'
#' Prepares a participant-level, condition-level time-course data set for a
#' conservative two-condition cluster-based permutation prototype. The helper
#' aggregates repeated observations to one value per participant, condition, and
#' time bin, then checks that the resulting data form a complete within-subject
#' time grid.
#'
#' This function is intended for exploratory time-course inference on already
#' preprocessed Gazepoint-derived signals. It does not perform blink correction,
#' artefact correction, baseline correction, filtering, or physiological
#' interpretation.
#'
#' @param data A data frame.
#' @param outcome_col Name of the numeric outcome column.
#' @param time_col Name of the numeric time column.
#' @param condition_col Name of the condition column.
#' @param participant_col Name of the participant identifier column.
#' @param condition_a Optional first condition level.
#' @param condition_b Optional second condition level.
#' @param time_bin_width Optional numeric time-bin width. If supplied, time is
#'   binned using `floor(time / time_bin_width) * time_bin_width`.
#' @param aggregation Aggregation rule for repeated rows within participant,
#'   condition, and time. Currently `"mean"` or `"median"`.
#' @param require_complete Logical. If `TRUE`, require a complete participant by
#'   condition by time grid.
#'
#' @return A data frame with columns `participant`, `condition`, `time`, and
#'   `value`, with class `gazepoint_timecourse_test_data`.
#'
#' @export
prepare_gazepoint_timecourse_test_data <- function(data,
                                                   outcome_col,
                                                   time_col,
                                                   condition_col,
                                                   participant_col,
                                                   condition_a = NULL,
                                                   condition_b = NULL,
                                                   time_bin_width = NULL,
                                                   aggregation = c("mean", "median"),
                                                   require_complete = TRUE) {
  .gp_cp_check_data_frame(data)
  .gp_cp_check_columns(
    data,
    c(outcome_col, time_col, condition_col, participant_col)
  )

  aggregation <- match.arg(aggregation)

  outcome <- data[[outcome_col]]
  time <- data[[time_col]]
  condition <- as.character(data[[condition_col]])
  participant <- as.character(data[[participant_col]])

  if (!is.numeric(outcome)) {
    stop("`outcome_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(time)) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(time_bin_width)) {
    if (!is.numeric(time_bin_width) || length(time_bin_width) != 1L ||
        !is.finite(time_bin_width) || time_bin_width <= 0) {
      stop("`time_bin_width` must be a positive numeric scalar.", call. = FALSE)
    }

    time <- floor(time / time_bin_width) * time_bin_width
  }

  keep <- is.finite(outcome) &
    is.finite(time) &
    !is.na(condition) &
    !is.na(participant)

  x <- data.frame(
    participant = participant[keep],
    condition = condition[keep],
    time = time[keep],
    value = outcome[keep],
    stringsAsFactors = FALSE
  )

  if (!nrow(x)) {
    stop("No complete finite rows remain after filtering.", call. = FALSE)
  }

  condition_levels <- sort(unique(x$condition))

  if (is.null(condition_a) || is.null(condition_b)) {
    if (length(condition_levels) != 2L) {
      stop(
        "Exactly two condition levels are required, or provide `condition_a` and `condition_b`.",
        call. = FALSE
      )
    }

    condition_a <- condition_levels[1]
    condition_b <- condition_levels[2]
  }

  if (identical(condition_a, condition_b)) {
    stop("`condition_a` and `condition_b` must be different.", call. = FALSE)
  }

  wanted_conditions <- c(condition_a, condition_b)

  if (!all(wanted_conditions %in% condition_levels)) {
    stop("`condition_a` and/or `condition_b` not found in `condition_col`.", call. = FALSE)
  }

  x <- x[x$condition %in% wanted_conditions, , drop = FALSE]
  x$condition <- factor(x$condition, levels = wanted_conditions)

  group_key <- interaction(
    x$participant,
    x$condition,
    x$time,
    drop = TRUE,
    lex.order = TRUE
  )

  split_values <- split(x$value, group_key)

  value <- if (identical(aggregation, "mean")) {
    vapply(split_values, mean, numeric(1), na.rm = TRUE)
  } else {
    vapply(split_values, stats::median, numeric(1), na.rm = TRUE)
  }

  key_parts <- do.call(
    rbind,
    strsplit(names(value), ".", fixed = TRUE)
  )

  # interaction() can be awkward if original values contain periods.
  # Therefore rebuild using aggregate() for safety.
  if (identical(aggregation, "mean")) {
    out <- stats::aggregate(
      value ~ participant + condition + time,
      data = x,
      FUN = mean
    )
  } else {
    out <- stats::aggregate(
      value ~ participant + condition + time,
      data = x,
      FUN = stats::median
    )
  }

  out$participant <- as.character(out$participant)
  out$condition <- factor(as.character(out$condition), levels = wanted_conditions)
  out$time <- as.numeric(out$time)
  out$value <- as.numeric(out$value)

  out <- out[order(out$participant, out$condition, out$time), , drop = FALSE]
  row.names(out) <- NULL

  .gp_cp_validate_complete_grid(
    out,
    require_complete = require_complete
  )

  attr(out, "gpbiometrics_settings") <- list(
    outcome_col = outcome_col,
    time_col = time_col,
    condition_col = condition_col,
    participant_col = participant_col,
    condition_a = condition_a,
    condition_b = condition_b,
    time_bin_width = time_bin_width,
    aggregation = aggregation,
    require_complete = require_complete
  )

  class(out) <- c("gazepoint_timecourse_test_data", class(out))

  out
}

#' Run a conservative cluster-based permutation test for Gazepoint time courses
#'
#' Runs a narrow within-subject, two-condition, one-dimensional cluster-based
#' permutation test on participant-level Gazepoint-derived time courses.
#'
#' The function computes a paired t-statistic at each time point using
#' participant-level condition differences, forms temporal clusters from
#' adjacent suprathreshold time points, uses summed absolute t-statistics as
#' cluster mass, and compares observed cluster masses with a sign-flip
#' permutation null distribution.
#'
#' @section Caution:
#' This helper tests the global null of no condition difference anywhere in the
#' tested time range. A significant cluster indicates evidence against that
#' global null under the permutation scheme. It does not establish the precise
#' onset, offset, latency, or physiological timing of an effect. Avoid wording
#' such as "the effect starts at X ms". Prefer conservative wording such as
#' "the cluster-based permutation test indicated a condition difference in the
#' tested time course".
#'
#' @param data A data frame, preferably returned by
#'   [prepare_gazepoint_timecourse_test_data()].
#' @param outcome_col Name of the numeric outcome column.
#' @param time_col Name of the numeric time column.
#' @param condition_col Name of the condition column.
#' @param participant_col Name of the participant identifier column.
#' @param design Currently only `"within"` is supported.
#' @param condition_a Optional first condition level. The tested difference is
#'   `condition_a - condition_b`.
#' @param condition_b Optional second condition level.
#' @param n_permutations Number of sign-flip permutations.
#' @param cluster_forming_alpha Per-time-point alpha used only to form clusters.
#' @param cluster_alpha Cluster-level alpha used for the `significant` flag.
#' @param tail Test tail. Currently `"two.sided"`, `"positive"`, or `"negative"`.
#' @param seed Optional random seed.
#' @param time_bin_width Optional time-bin width passed to
#'   [prepare_gazepoint_timecourse_test_data()] when the input has not already
#'   been prepared.
#' @param aggregation Aggregation rule passed to
#'   [prepare_gazepoint_timecourse_test_data()] when needed.
#'
#' @return An object of class `gazepoint_cluster_permutation`.
#'
#' @export
run_gazepoint_cluster_permutation <- function(data,
                                              outcome_col = "value",
                                              time_col = "time",
                                              condition_col = "condition",
                                              participant_col = "participant",
                                              design = "within",
                                              condition_a = NULL,
                                              condition_b = NULL,
                                              n_permutations = 1000,
                                              cluster_forming_alpha = 0.05,
                                              cluster_alpha = 0.05,
                                              tail = c("two.sided", "positive", "negative"),
                                              seed = NULL,
                                              time_bin_width = NULL,
                                              aggregation = c("mean", "median")) {
  .gp_cp_check_data_frame(data)

  design <- match.arg(design, choices = "within")
  tail <- match.arg(tail)
  aggregation <- match.arg(aggregation)

  if (!is.numeric(n_permutations) || length(n_permutations) != 1L ||
      !is.finite(n_permutations) || n_permutations < 1) {
    stop("`n_permutations` must be a positive numeric scalar.", call. = FALSE)
  }

  n_permutations <- as.integer(n_permutations)

  if (!is.numeric(cluster_forming_alpha) || length(cluster_forming_alpha) != 1L ||
      !is.finite(cluster_forming_alpha) ||
      cluster_forming_alpha <= 0 || cluster_forming_alpha >= 1) {
    stop("`cluster_forming_alpha` must be between 0 and 1.", call. = FALSE)
  }

  if (!is.numeric(cluster_alpha) || length(cluster_alpha) != 1L ||
      !is.finite(cluster_alpha) || cluster_alpha <= 0 || cluster_alpha >= 1) {
    stop("`cluster_alpha` must be between 0 and 1.", call. = FALSE)
  }

  prepared <- prepare_gazepoint_timecourse_test_data(
    data = data,
    outcome_col = outcome_col,
    time_col = time_col,
    condition_col = condition_col,
    participant_col = participant_col,
    condition_a = condition_a,
    condition_b = condition_b,
    time_bin_width = time_bin_width,
    aggregation = aggregation,
    require_complete = TRUE
  )

  settings <- attr(prepared, "gpbiometrics_settings")
  condition_a <- settings$condition_a
  condition_b <- settings$condition_b

  matrices <- .gp_cp_make_condition_matrices(
    prepared,
    condition_a = condition_a,
    condition_b = condition_b
  )

  differences <- matrices$a - matrices$b
  n_participants <- nrow(differences)
  n_times <- ncol(differences)

  if (n_participants < 3L) {
    stop("At least three complete participants are required.", call. = FALSE)
  }

  observed <- .gp_cp_timewise_t(differences)

  df <- n_participants - 1L
  threshold_value <- .gp_cp_t_threshold(
    df = df,
    alpha = cluster_forming_alpha,
    tail = tail
  )

  observed_clusters <- .gp_cp_find_clusters(
    stat = observed$t,
    times = matrices$times,
    threshold_value = threshold_value,
    tail = tail
  )

  if (!is.null(seed)) {
    old_seed <- if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
      get(".Random.seed", envir = .GlobalEnv, inherits = FALSE)
    } else {
      NULL
    }

    on.exit({
      if (is.null(old_seed)) {
        if (exists(".Random.seed", envir = .GlobalEnv, inherits = FALSE)) {
          rm(".Random.seed", envir = .GlobalEnv)
        }
      } else {
        assign(".Random.seed", old_seed, envir = .GlobalEnv)
      }
    }, add = TRUE)

    set.seed(seed)
  }

  null_distribution <- .gp_cp_permute_within_subject(
    differences = differences,
    times = matrices$times,
    n_permutations = n_permutations,
    threshold_value = threshold_value,
    tail = tail
  )

  clusters <- .gp_cp_attach_cluster_p_values(
    clusters = observed_clusters,
    null_distribution = null_distribution,
    cluster_alpha = cluster_alpha
  )

  timewise <- data.frame(
    time = matrices$times,
    t = observed$t,
    p_uncorrected = observed$p,
    mean_difference = observed$mean,
    sd_difference = observed$sd,
    n = observed$n,
    stringsAsFactors = FALSE
  )

  condition_summary <- stats::aggregate(
    value ~ condition + time,
    data = prepared,
    FUN = function(z) c(
      mean = mean(z, na.rm = TRUE),
      se = stats::sd(z, na.rm = TRUE) / sqrt(sum(is.finite(z)))
    )
  )

  condition_summary <- data.frame(
    condition = condition_summary$condition,
    time = condition_summary$time,
    mean = condition_summary$value[, "mean"],
    se = condition_summary$value[, "se"],
    stringsAsFactors = FALSE
  )

  warnings <- c(
    "Within-subject sign-flip permutations only.",
    "Two-condition one-dimensional time-course test only.",
    "Cluster timing is descriptive and must not be interpreted as precise onset or offset."
  )

  out <- list(
    timewise = timewise,
    clusters = clusters,
    null_distribution = null_distribution,
    condition_summary = condition_summary,
    prepared_data = prepared,
    settings = list(
      design = design,
      condition_a = condition_a,
      condition_b = condition_b,
      n_permutations = n_permutations,
      cluster_forming_alpha = cluster_forming_alpha,
      cluster_alpha = cluster_alpha,
      tail = tail,
      threshold_value = threshold_value,
      df = df,
      n_participants = n_participants,
      n_times = n_times,
      seed = seed,
      aggregation = aggregation,
      time_bin_width = time_bin_width
    ),
    warnings = warnings,
    call = match.call()
  )

  class(out) <- "gazepoint_cluster_permutation"

  out
}

#' Summarize Gazepoint time clusters
#'
#' Returns a compact cluster-level summary table from a
#' `gazepoint_cluster_permutation` object.
#'
#' @param x Object returned by [run_gazepoint_cluster_permutation()].
#' @param alpha Optional cluster-level alpha. If `NULL`, the alpha stored in the
#'   object is used.
#'
#' @return A data frame.
#'
#' @export
summarize_gazepoint_time_clusters <- function(x, alpha = NULL) {
  if (!inherits(x, "gazepoint_cluster_permutation")) {
    stop("`x` must be returned by run_gazepoint_cluster_permutation().", call. = FALSE)
  }

  if (is.null(alpha)) {
    alpha <- x$settings$cluster_alpha
  }

  clusters <- x$clusters

  if (!nrow(clusters)) {
    return(clusters)
  }

  clusters$significant <- clusters$p_value <= alpha
  clusters
}

#' Plot Gazepoint cluster permutation results
#'
#' Plots condition-level time courses and highlights clusters that pass the
#' cluster-level alpha threshold. The shaded regions are descriptive aids only;
#' they should not be interpreted as precise effect onset or offset estimates.
#'
#' @param x Object returned by [run_gazepoint_cluster_permutation()].
#' @param alpha Optional cluster-level alpha. If `NULL`, the alpha stored in the
#'   object is used.
#' @param show_all_clusters Logical. If `FALSE`, only clusters with
#'   `p <= alpha` are shaded.
#'
#' @return A `ggplot` object.
#'
#' @export
plot_gazepoint_cluster_permutation <- function(x,
                                               alpha = NULL,
                                               show_all_clusters = FALSE) {
  if (!inherits(x, "gazepoint_cluster_permutation")) {
    stop("`x` must be returned by run_gazepoint_cluster_permutation().", call. = FALSE)
  }

  if (!requireNamespace("ggplot2", quietly = TRUE)) {
    stop("Package `ggplot2` is required for plotting.", call. = FALSE)
  }

  if (is.null(alpha)) {
    alpha <- x$settings$cluster_alpha
  }

  summary_data <- x$condition_summary
  clusters <- summarize_gazepoint_time_clusters(x, alpha = alpha)

  if (nrow(clusters) && !show_all_clusters) {
    clusters <- clusters[clusters$significant, , drop = FALSE]
  }

  p <- ggplot2::ggplot(
    summary_data,
    ggplot2::aes(
      x = time,
      y = mean,
      group = condition,
      linetype = condition
    )
  )

  if (nrow(clusters)) {
    for (i in seq_len(nrow(clusters))) {
      p <- p +
        ggplot2::annotate(
          "rect",
          xmin = clusters$start_time[i],
          xmax = clusters$end_time[i],
          ymin = -Inf,
          ymax = Inf,
          alpha = 0.12
        )
    }
  }

  p +
    ggplot2::geom_line(linewidth = 0.7) +
    ggplot2::geom_ribbon(
      ggplot2::aes(
        ymin = mean - se,
        ymax = mean + se,
        group = condition
      ),
      alpha = 0.12,
      linetype = 0
    ) +
    ggplot2::labs(
      x = "Time",
      y = "Mean signal",
      linetype = "Condition",
      title = "Gazepoint cluster permutation time course",
      subtitle = "Shaded regions indicate cluster-level p values at or below alpha; timing is descriptive."
    ) +
    ggplot2::theme_minimal()
}

#' @export
print.gazepoint_cluster_permutation <- function(x, ...) {
  cat("Gazepoint cluster permutation test\n")
  cat("Design:", x$settings$design, "\n")
  cat("Conditions:", x$settings$condition_a, "-", x$settings$condition_b, "\n")
  cat("Participants:", x$settings$n_participants, "\n")
  cat("Time points:", x$settings$n_times, "\n")
  cat("Permutations:", x$settings$n_permutations, "\n")
  cat("Cluster-forming alpha:", x$settings$cluster_forming_alpha, "\n")
  cat("Cluster-level alpha:", x$settings$cluster_alpha, "\n")

  clusters <- summarize_gazepoint_time_clusters(x)

  if (!nrow(clusters)) {
    cat("Clusters: none\n")
  } else {
    cat("Clusters:", nrow(clusters), "\n")
    print(clusters[, c(
      "cluster_id",
      "direction",
      "start_time",
      "end_time",
      "n_timepoints",
      "mass",
      "p_value",
      "significant"
    )], row.names = FALSE)
  }

  invisible(x)
}

.gp_cp_check_data_frame <- function(data) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  invisible(TRUE)
}

.gp_cp_check_columns <- function(data, columns) {
  missing <- setdiff(columns, names(data))

  if (length(missing)) {
    stop(
      "Missing required column(s): ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  invisible(TRUE)
}

.gp_cp_validate_complete_grid <- function(data, require_complete = TRUE) {
  subjects <- sort(unique(data$participant))
  conditions <- levels(data$condition)
  times <- sort(unique(data$time))

  expected <- length(subjects) * length(conditions) * length(times)

  if (nrow(data) != expected) {
    message <- paste0(
      "The prepared data are not a complete participant by condition by time grid. ",
      "Expected ", expected, " rows but found ", nrow(data), "."
    )

    if (require_complete) {
      stop(message, call. = FALSE)
    }

    warning(message, call. = FALSE)
  }

  counts <- stats::aggregate(
    value ~ participant + condition + time,
    data = data,
    FUN = length
  )

  if (any(counts$value != 1L)) {
    stop(
      "Prepared data must contain exactly one value per participant, condition, and time.",
      call. = FALSE
    )
  }

  invisible(TRUE)
}

.gp_cp_make_condition_matrices <- function(data, condition_a, condition_b) {
  subjects <- sort(unique(data$participant))
  times <- sort(unique(data$time))

  make_matrix <- function(condition_level) {
    z <- data[data$condition == condition_level, , drop = FALSE]

    mat <- matrix(
      NA_real_,
      nrow = length(subjects),
      ncol = length(times),
      dimnames = list(subjects, as.character(times))
    )

    row_index <- match(z$participant, subjects)
    col_index <- match(z$time, times)

    mat[cbind(row_index, col_index)] <- z$value
    mat
  }

  a <- make_matrix(condition_a)
  b <- make_matrix(condition_b)

  if (anyNA(a) || anyNA(b)) {
    stop(
      "Complete condition matrices could not be created. Check missing participant/time cells.",
      call. = FALSE
    )
  }

  list(
    a = a,
    b = b,
    subjects = subjects,
    times = times
  )
}

.gp_cp_timewise_t <- function(differences) {
  n <- nrow(differences)

  means <- colMeans(differences, na.rm = TRUE)
  sds <- apply(differences, 2L, stats::sd, na.rm = TRUE)

  t_values <- ifelse(
    is.finite(sds) & sds > 0,
    means / (sds / sqrt(n)),
    0
  )

  p_values <- 2 * stats::pt(-abs(t_values), df = n - 1L)

  list(
    t = as.numeric(t_values),
    p = as.numeric(p_values),
    mean = as.numeric(means),
    sd = as.numeric(sds),
    n = rep.int(n, length(t_values))
  )
}

.gp_cp_t_threshold <- function(df, alpha, tail) {
  if (identical(tail, "two.sided")) {
    stats::qt(1 - alpha / 2, df = df)
  } else {
    stats::qt(1 - alpha, df = df)
  }
}

.gp_cp_find_clusters <- function(stat, times, threshold_value, tail) {
  if (identical(tail, "positive")) {
    return(.gp_cp_find_directional_clusters(
      stat = stat,
      times = times,
      include = stat >= threshold_value,
      direction = "positive"
    ))
  }

  if (identical(tail, "negative")) {
    return(.gp_cp_find_directional_clusters(
      stat = stat,
      times = times,
      include = stat <= -threshold_value,
      direction = "negative"
    ))
  }

  positive <- .gp_cp_find_directional_clusters(
    stat = stat,
    times = times,
    include = stat >= threshold_value,
    direction = "positive"
  )

  negative <- .gp_cp_find_directional_clusters(
    stat = stat,
    times = times,
    include = stat <= -threshold_value,
    direction = "negative"
  )

  out <- rbind(positive, negative)
  row.names(out) <- NULL

  if (nrow(out)) {
    out$cluster_id <- seq_len(nrow(out))
  }

  out
}

.gp_cp_empty_clusters <- function() {
  data.frame(
    cluster_id = integer(),
    direction = character(),
    start_index = integer(),
    end_index = integer(),
    start_time = numeric(),
    end_time = numeric(),
    n_timepoints = integer(),
    signed_mass = numeric(),
    mass = numeric(),
    p_value = numeric(),
    significant = logical(),
    stringsAsFactors = FALSE
  )
}

.gp_cp_find_directional_clusters <- function(stat, times, include, direction) {
  include[is.na(include)] <- FALSE

  if (!any(include)) {
    return(.gp_cp_empty_clusters())
  }

  runs <- rle(include)
  ends <- cumsum(runs$lengths)
  starts <- ends - runs$lengths + 1L

  cluster_rows <- which(runs$values)

  if (!length(cluster_rows)) {
    return(.gp_cp_empty_clusters())
  }

  out <- lapply(seq_along(cluster_rows), function(i) {
    run_index <- cluster_rows[i]
    idx <- starts[run_index]:ends[run_index]
    signed_mass <- sum(stat[idx], na.rm = TRUE)

    data.frame(
      cluster_id = i,
      direction = direction,
      start_index = min(idx),
      end_index = max(idx),
      start_time = times[min(idx)],
      end_time = times[max(idx)],
      n_timepoints = length(idx),
      signed_mass = signed_mass,
      mass = sum(abs(stat[idx]), na.rm = TRUE),
      p_value = NA_real_,
      significant = NA,
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, out)
}

.gp_cp_permute_within_subject <- function(differences,
                                          times,
                                          n_permutations,
                                          threshold_value,
                                          tail) {
  n_subjects <- nrow(differences)
  null_distribution <- numeric(n_permutations)

  for (i in seq_len(n_permutations)) {
    signs <- sample(c(-1, 1), size = n_subjects, replace = TRUE)
    permuted <- differences * signs
    perm_t <- .gp_cp_timewise_t(permuted)$t

    perm_clusters <- .gp_cp_find_clusters(
      stat = perm_t,
      times = times,
      threshold_value = threshold_value,
      tail = tail
    )

    null_distribution[i] <- if (nrow(perm_clusters)) {
      max(perm_clusters$mass, na.rm = TRUE)
    } else {
      0
    }
  }

  null_distribution
}

.gp_cp_attach_cluster_p_values <- function(clusters,
                                           null_distribution,
                                           cluster_alpha) {
  if (!nrow(clusters)) {
    return(clusters)
  }

  clusters$p_value <- vapply(
    clusters$mass,
    function(mass) {
      (1 + sum(null_distribution >= mass, na.rm = TRUE)) /
        (length(null_distribution) + 1)
    },
    numeric(1)
  )

  clusters$significant <- clusters$p_value <= cluster_alpha

  clusters
}
