#' Optimise subject-specific cvxEDA slow time constant
#'
#' Performs a dependency-light grid search over the slow Bateman impulse-response
#' time constant used in cvxEDA-style EDA decomposition workflows. The default
#' fast time constant is fixed at 0.7 seconds and the slow time constant is
#' searched between 2 and 4 seconds. This function does not run the original
#' cvxEDA optimisation; it provides a subject-specific tau-selection bridge for
#' downstream cvxEDA-style workflows.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns, usually participant/session.
#' @param tau0_grid Candidate slow time constants.
#' @param tau1 Fixed fast time constant.
#' @param sampling_rate Optional sampling rate in Hz. If `NULL`, estimated from
#'   `time_col`.
#' @param ridge_lambda Small ridge penalty used in frequency-domain
#'   deconvolution.
#' @param max_irf_seconds Maximum impulse-response duration.
#'
#' @return A list with `overview`, `best_tau`, `optimization_table`, and
#'   `settings`.
#' @export
optimize_gazepoint_cvxeda_tau <- function(dat,
                                          eda_col = "GSR_US",
                                          time_col = "CNT",
                                          group_cols = NULL,
                                          tau0_grid = seq(2, 4, by = 0.25),
                                          tau1 = 0.7,
                                          sampling_rate = NULL,
                                          ridge_lambda = 0.01,
                                          max_irf_seconds = 20) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!eda_col %in% names(dat)) {
    stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  tau0_grid <- sort(unique(as.numeric(tau0_grid)))

  if (length(tau0_grid) == 0 ||
      any(!is.finite(tau0_grid)) ||
      any(tau0_grid <= tau1)) {
    stop("`tau0_grid` must contain finite values larger than `tau1`.", call. = FALSE)
  }

  groups <- gpbiometrics_cvxeda_tau_split(dat, group_cols)

  rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    eda <- dat[[eda_col]][idx]
    fs <- gpbiometrics_cvxeda_tau_sampling_rate(time, sampling_rate)

    finite_eda <- is.finite(eda)

    if (!is.finite(fs) || fs <= 0 || sum(finite_eda) < 20) {
      for (tau0 in tau0_grid) {
        rows[[row_id]] <- data.frame(
          group_id = group_id,
          tau0 = tau0,
          tau1 = tau1,
          sampling_rate_hz = fs,
          n_samples = length(idx),
          n_finite = sum(finite_eda),
          rmse = NA_real_,
          mae = NA_real_,
          residual_sd = NA_real_,
          correlation = NA_real_,
          status = "insufficient_signal_or_sampling_rate",
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
      }
      next
    }

    y <- gpbiometrics_cvxeda_tau_fill(eda)
    y <- y - mean(y, na.rm = TRUE)

    for (tau0 in tau0_grid) {
      fit <- gpbiometrics_cvxeda_tau_fit(
        y = y,
        sampling_rate = fs,
        tau0 = tau0,
        tau1 = tau1,
        ridge_lambda = ridge_lambda,
        max_irf_seconds = max_irf_seconds
      )

      rows[[row_id]] <- data.frame(
        group_id = group_id,
        tau0 = tau0,
        tau1 = tau1,
        sampling_rate_hz = fs,
        n_samples = length(idx),
        n_finite = sum(finite_eda),
        rmse = fit$rmse,
        mae = fit$mae,
        residual_sd = fit$residual_sd,
        correlation = fit$correlation,
        status = fit$status,
        stringsAsFactors = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  optimization_table <- do.call(rbind, rows)
  rownames(optimization_table) <- NULL

  best_rows <- lapply(split(optimization_table, optimization_table$group_id), function(d) {
    ok <- d[is.finite(d$rmse), , drop = FALSE]

    if (nrow(ok) == 0) {
      return(d[1, , drop = FALSE])
    }

    ok[which.min(ok$rmse), , drop = FALSE]
  })

  best_tau <- do.call(rbind, best_rows)
  rownames(best_tau) <- NULL

  best_tau$status <- ifelse(
    is.finite(best_tau$rmse),
    "best_tau_selected",
    "best_tau_not_selected"
  )

  overview <- data.frame(
    group_count = length(groups),
    candidate_tau_count = length(tau0_grid),
    optimization_rows = nrow(optimization_table),
    successful_groups = sum(best_tau$status == "best_tau_selected"),
    problem_groups = sum(best_tau$status != "best_tau_selected"),
    status = if (all(best_tau$status == "best_tau_selected")) {
      "cvxeda_tau_optimization_complete"
    } else if (any(best_tau$status == "best_tau_selected")) {
      "cvxeda_tau_optimization_partial"
    } else {
      "cvxeda_tau_optimization_failed"
    },
    interpretation = paste(
      "The selected tau0 minimises a dependency-light reconstruction residual.",
      "This is a cvxEDA parameter-selection bridge and not the original cvxEDA convex optimisation."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      best_tau = best_tau,
      optimization_table = optimization_table,
      settings = list(
        eda_col = eda_col,
        time_col = time_col,
        group_cols = group_cols,
        tau0_grid = tau0_grid,
        tau1 = tau1,
        sampling_rate = sampling_rate,
        ridge_lambda = ridge_lambda,
        max_irf_seconds = max_irf_seconds
      )
    ),
    class = c("gazepoint_cvxeda_tau_optimization", "list")
  )
}

gpbiometrics_cvxeda_tau_split <- function(dat, group_cols) {
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

gpbiometrics_cvxeda_tau_sampling_rate <- function(time, sampling_rate = NULL) {
  if (!is.null(sampling_rate)) {
    return(sampling_rate)
  }

  time <- time[is.finite(time)]

  if (length(time) < 3) {
    return(NA_real_)
  }

  dt <- diff(time)
  dt <- dt[is.finite(dt) & dt > 0]

  if (length(dt) == 0) {
    return(NA_real_)
  }

  median_dt <- stats::median(dt)

  if (median_dt > 10) {
    1000 / median_dt
  } else {
    1 / median_dt
  }
}

gpbiometrics_cvxeda_tau_fill <- function(x) {
  idx <- seq_along(x)
  finite <- is.finite(x)

  if (all(finite)) {
    return(x)
  }

  if (sum(finite) == 0) {
    return(rep(0, length(x)))
  }

  if (sum(finite) == 1) {
    return(rep(x[finite][1], length(x)))
  }

  stats::approx(idx[finite], x[finite], xout = idx, rule = 2)$y
}

gpbiometrics_cvxeda_tau_irf <- function(sampling_rate,
                                        tau0,
                                        tau1,
                                        max_irf_seconds = 20) {
  t <- seq(0, max_irf_seconds, by = 1 / sampling_rate)

  h <- exp(-t / tau0) - exp(-t / tau1)
  h[h < 0] <- 0

  if (sum(h) > 0) {
    h <- h / sum(h)
  }

  h
}

gpbiometrics_cvxeda_tau_fit <- function(y,
                                        sampling_rate,
                                        tau0,
                                        tau1,
                                        ridge_lambda = 0.01,
                                        max_irf_seconds = 20) {
  h <- gpbiometrics_cvxeda_tau_irf(
    sampling_rate = sampling_rate,
    tau0 = tau0,
    tau1 = tau1,
    max_irf_seconds = max_irf_seconds
  )

  n <- length(y)
  n_conv <- n + length(h) - 1
  n_fft <- 2^ceiling(log2(n_conv))

  y_pad <- c(y, rep(0, n_fft - n))
  h_pad <- c(h, rep(0, n_fft - length(h)))

  y_fft <- stats::fft(y_pad)
  h_fft <- stats::fft(h_pad)

  driver_fft <- Conj(h_fft) * y_fft / (Mod(h_fft)^2 + ridge_lambda)
  recon_fft <- h_fft * driver_fft

  recon <- Re(stats::fft(recon_fft, inverse = TRUE) / n_fft)[seq_len(n)]

  residual <- y - recon

  data.frame(
    rmse = sqrt(mean(residual^2, na.rm = TRUE)),
    mae = mean(abs(residual), na.rm = TRUE),
    residual_sd = stats::sd(residual, na.rm = TRUE),
    correlation = suppressWarnings(stats::cor(y, recon, use = "pairwise.complete.obs")),
    status = "tau_fit_evaluated",
    stringsAsFactors = FALSE
  )
}
