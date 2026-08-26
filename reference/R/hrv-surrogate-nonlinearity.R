#' Test HRV nonlinearity using surrogate data
#'
#' Tests whether a nonlinear HRV statistic differs from surrogate RR/IBI
#' sequences. This is a screening tool for evidence inconsistent with a simple
#' linear stochastic null process. It does not prove deterministic chaos or
#' diagnose any condition.
#'
#' @param dat A data frame containing IBI/RR intervals.
#' @param ibi_col Numeric IBI/RR interval column.
#' @param group_cols Optional grouping columns.
#' @param metric Nonlinear statistic to test.
#' @param n_surrogates Number of surrogate series per group.
#' @param surrogate_method `"phase_randomized"` or `"shuffle"`.
#' @param m Embedding dimension for entropy metrics.
#' @param r_multiplier Tolerance multiplier for entropy metrics.
#' @param statistic_fun Optional custom statistic function accepting numeric x.
#' @param seed Optional random seed.
#'
#' @return A list with `overview`, `results`, `surrogate_statistics`, and
#'   `settings`.
#' @export
test_gazepoint_hrv_nonlinearity <- function(dat,
                                            ibi_col = "IBI",
                                            group_cols = NULL,
                                            metric = c(
                                              "sample_entropy",
                                              "approximate_entropy",
                                              "sd1_sd2_ratio"
                                            ),
                                            n_surrogates = 99,
                                            surrogate_method = c(
                                              "phase_randomized",
                                              "shuffle"
                                            ),
                                            m = 2,
                                            r_multiplier = 0.2,
                                            statistic_fun = NULL,
                                            seed = NULL) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!ibi_col %in% names(dat)) {
    stop("Column `", ibi_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[ibi_col]])) {
    stop("`ibi_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  metric <- match.arg(metric)
  surrogate_method <- match.arg(surrogate_method)

  if (!is.numeric(n_surrogates) ||
      length(n_surrogates) != 1 ||
      !is.finite(n_surrogates) ||
      n_surrogates < 1) {
    stop("`n_surrogates` must be a positive integer.", call. = FALSE)
  }

  n_surrogates <- as.integer(n_surrogates)

  if (!is.null(seed)) {
    set.seed(seed)
  }

  groups <- gpbiometrics_nonlinearity_split(dat, group_cols)

  result_rows <- list()
  surrogate_rows <- list()
  surrogate_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    x <- dat[[ibi_col]][idx]
    x <- x[is.finite(x) & x > 0]

    observed <- gpbiometrics_nonlinearity_statistic(
      x = x,
      metric = metric,
      m = m,
      r_multiplier = r_multiplier,
      statistic_fun = statistic_fun
    )

    surrogate_values <- rep(NA_real_, n_surrogates)

    if (length(x) >= 10 && is.finite(observed)) {
      for (i in seq_len(n_surrogates)) {
        sx <- gpbiometrics_nonlinearity_surrogate(
          x,
          method = surrogate_method
        )

        surrogate_values[i] <- gpbiometrics_nonlinearity_statistic(
          x = sx,
          metric = metric,
          m = m,
          r_multiplier = r_multiplier,
          statistic_fun = statistic_fun
        )

        surrogate_rows[[surrogate_id]] <- data.frame(
          group_id = group_id,
          surrogate_index = i,
          surrogate_statistic = surrogate_values[i],
          stringsAsFactors = FALSE
        )

        surrogate_id <- surrogate_id + 1L
      }
    }

    finite_surrogates <- surrogate_values[is.finite(surrogate_values)]

    if (length(finite_surrogates) > 0 && is.finite(observed)) {
      p_greater <- (1 + sum(finite_surrogates >= observed)) /
        (length(finite_surrogates) + 1)

      p_less <- (1 + sum(finite_surrogates <= observed)) /
        (length(finite_surrogates) + 1)

      p_two_sided <- min(1, 2 * min(p_greater, p_less))

      z_score <- if (stats::sd(finite_surrogates) > 0) {
        (observed - mean(finite_surrogates)) / stats::sd(finite_surrogates)
      } else {
        NA_real_
      }

      status <- if (p_two_sided < 0.05) {
        "surrogate_difference_detected"
      } else {
        "surrogate_difference_not_detected"
      }
    } else {
      p_greater <- NA_real_
      p_less <- NA_real_
      p_two_sided <- NA_real_
      z_score <- NA_real_
      status <- "insufficient_information"
    }

    result_rows[[group_id]] <- data.frame(
      group_id = group_id,
      n_intervals = length(x),
      observed_statistic = observed,
      surrogate_mean = if (length(finite_surrogates) > 0) {
        mean(finite_surrogates)
      } else {
        NA_real_
      },
      surrogate_sd = if (length(finite_surrogates) > 1) {
        stats::sd(finite_surrogates)
      } else {
        NA_real_
      },
      p_greater = p_greater,
      p_less = p_less,
      p_two_sided = p_two_sided,
      z_score = z_score,
      status = status,
      stringsAsFactors = FALSE
    )
  }

  results <- do.call(rbind, result_rows)
  rownames(results) <- NULL

  surrogate_statistics <- if (length(surrogate_rows) > 0) {
    do.call(rbind, surrogate_rows)
  } else {
    data.frame()
  }

  overview <- data.frame(
    group_count = length(groups),
    result_rows = nrow(results),
    n_surrogates = n_surrogates,
    metric = metric,
    surrogate_method = surrogate_method,
    significant_groups = sum(results$status == "surrogate_difference_detected"),
    status = if (all(results$status != "insufficient_information")) {
      "surrogate_nonlinearity_test_complete"
    } else if (any(results$status != "insufficient_information")) {
      "surrogate_nonlinearity_test_partial"
    } else {
      "surrogate_nonlinearity_test_failed"
    },
    interpretation = paste(
      "A significant surrogate test indicates that the selected statistic differs from the surrogate null distribution.",
      "It does not prove deterministic chaos, clinical status, emotion, stress, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      results = results,
      surrogate_statistics = surrogate_statistics,
      settings = list(
        ibi_col = ibi_col,
        group_cols = group_cols,
        metric = metric,
        n_surrogates = n_surrogates,
        surrogate_method = surrogate_method,
        m = m,
        r_multiplier = r_multiplier,
        custom_statistic = !is.null(statistic_fun),
        seed = seed
      )
    ),
    class = c("gazepoint_hrv_nonlinearity_test", "list")
  )
}

gpbiometrics_nonlinearity_split <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(list(all_rows = seq_len(nrow(dat))))
  }

  gf <- dat[group_cols]
  gf[] <- lapply(gf, function(x) {
    x <- as.character(x)
    x[is.na(x)] <- "<NA>"
    x
  })

  split(seq_len(nrow(dat)), do.call(paste, c(gf, sep = " | ")))
}

gpbiometrics_nonlinearity_statistic <- function(x,
                                                metric,
                                                m = 2,
                                                r_multiplier = 0.2,
                                                statistic_fun = NULL) {
  x <- x[is.finite(x)]

  if (length(x) < 10 || stats::sd(x) == 0) {
    return(NA_real_)
  }

  if (!is.null(statistic_fun)) {
    return(as.numeric(statistic_fun(x))[1])
  }

  r <- r_multiplier * stats::sd(x)

  if (metric == "sample_entropy") {
    return(gpbiometrics_sample_entropy(x, m = m, r = r))
  }

  if (metric == "approximate_entropy") {
    return(gpbiometrics_approximate_entropy(x, m = m, r = r))
  }

  if (metric == "sd1_sd2_ratio") {
    dx <- diff(x)
    sdnn <- stats::sd(x)
    diff_var <- stats::var(dx, na.rm = TRUE)
    sd1 <- sqrt(diff_var / 2)
    sd2 <- sqrt(max((2 * sdnn^2) - (0.5 * diff_var), 0))

    if (is.finite(sd2) && sd2 > 0) {
      return(sd1 / sd2)
    }

    return(NA_real_)
  }

  NA_real_
}

gpbiometrics_nonlinearity_surrogate <- function(x,
                                                method = "phase_randomized") {
  x <- x[is.finite(x)]

  if (method == "shuffle") {
    return(sample(x, length(x), replace = FALSE))
  }

  gpbiometrics_phase_randomized_surrogate(x)
}

gpbiometrics_phase_randomized_surrogate <- function(x) {
  n <- length(x)

  if (n < 4) {
    return(sample(x, length(x), replace = FALSE))
  }

  x_centered <- x - mean(x)
  fft_x <- stats::fft(x_centered)

  random_phase <- stats::runif(n, min = 0, max = 2 * pi)

  phase_multiplier <- exp(1i * random_phase)
  phase_multiplier[1] <- 1

  if (n %% 2 == 0) {
    phase_multiplier[(n / 2) + 1] <- 1
    positive <- 2:(n / 2)
    negative <- n:(n / 2 + 2)
  } else {
    positive <- 2:((n + 1) / 2)
    negative <- n:((n + 3) / 2)
  }

  phase_multiplier[negative] <- Conj(phase_multiplier[positive])

  surrogate <- Re(stats::fft(fft_x * phase_multiplier, inverse = TRUE) / n)
  surrogate <- surrogate + mean(x)

  surrogate
}
