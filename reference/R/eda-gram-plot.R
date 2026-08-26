#' Plot an EDA-gram-style time-frequency representation
#'
#' Creates a dependency-light EDA-gram-style representation using sliding-window
#' spectral power. This is inspired by EDA-gram visualisations, but it does not
#' implement a full sparse dictionary decomposition unless such a model is
#' supplied externally.
#'
#' @param dat A data frame containing EDA data.
#' @param eda_col Numeric EDA/conductance column.
#' @param time_col Numeric time column.
#' @param group_cols Optional grouping columns.
#' @param group_id_to_plot Optional group ID to plot. If `NULL`, plots the first
#'   available group.
#' @param sampling_rate Optional sampling rate in Hz. If `NULL`, estimated from
#'   `time_col`.
#' @param window_seconds Sliding-window length.
#' @param step_seconds Sliding-window step.
#' @param frequency_range Frequency range shown in Hz.
#' @param frequency_bins Number of frequency bins.
#' @param log_power Logical. If `TRUE`, plot log1p power.
#' @param plot Logical. If `TRUE`, draw the EDA-gram.
#' @param main Plot title.
#'
#' @return Invisibly returns a list with `overview`, `gram_table`,
#'   `plot_matrix`, and `settings`.
#' @export
plot_gazepoint_eda_gram <- function(dat,
                                    eda_col = "GSR_US",
                                    time_col = "CNT",
                                    group_cols = NULL,
                                    group_id_to_plot = NULL,
                                    sampling_rate = NULL,
                                    window_seconds = 30,
                                    step_seconds = 5,
                                    frequency_range = c(0.01, 0.50),
                                    frequency_bins = 64,
                                    log_power = TRUE,
                                    plot = TRUE,
                                    main = "EDA-gram") {
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

  frequency_grid <- seq(
    frequency_range[1],
    frequency_range[2],
    length.out = frequency_bins
  )

  groups <- gpbiometrics_edagram_split(dat, group_cols)

  gram_rows <- list()
  matrix_by_group <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]
    idx <- idx[order(dat[[time_col]][idx])]

    time <- dat[[time_col]][idx]
    eda <- dat[[eda_col]][idx]

    fs <- gpbiometrics_edagram_sampling_rate(time, sampling_rate)

    if (!is.finite(fs) || fs <= 0 || sum(is.finite(eda)) < 8) {
      next
    }

    min_time <- min(time, na.rm = TRUE)
    max_time <- max(time, na.rm = TRUE)

    starts <- seq(min_time, max_time - window_seconds, by = step_seconds)

    if (length(starts) == 0) {
      starts <- min_time
    }

    group_matrix <- matrix(
      NA_real_,
      nrow = length(starts),
      ncol = length(frequency_grid)
    )

    for (i in seq_along(starts)) {
      w_start <- starts[i]
      w_end <- w_start + window_seconds
      in_window <- is.finite(time) & time >= w_start & time <= w_end
      x <- eda[in_window]

      if (sum(is.finite(x)) < 8) {
        next
      }

      x <- gpbiometrics_edagram_fill(x)
      x <- x - mean(x, na.rm = TRUE)

      spec <- stats::spec.pgram(
        x,
        taper = 0.1,
        plot = FALSE,
        demean = TRUE,
        detrend = TRUE,
        fast = TRUE
      )

      freq <- spec$freq * fs
      power <- spec$spec

      interp_power <- stats::approx(
        x = freq,
        y = power,
        xout = frequency_grid,
        rule = 2
      )$y

      if (isTRUE(log_power)) {
        interp_power <- log1p(interp_power)
      }

      group_matrix[i, ] <- interp_power

      for (j in seq_along(frequency_grid)) {
        gram_rows[[row_id]] <- data.frame(
          group_id = group_id,
          window_index = i,
          window_start = w_start,
          window_end = w_end,
          window_midpoint = mean(c(w_start, w_end)),
          frequency_hz = frequency_grid[j],
          power = interp_power[j],
          status = "eda_gram_cell_created",
          stringsAsFactors = FALSE
        )
        row_id <- row_id + 1L
      }
    }

    matrix_by_group[[group_id]] <- list(
      group_id = group_id,
      window_midpoint = starts + window_seconds / 2,
      frequency_hz = frequency_grid,
      power_matrix = group_matrix
    )
  }

  gram_table <- if (length(gram_rows) > 0) {
    do.call(rbind, gram_rows)
  } else {
    data.frame()
  }

  if (length(matrix_by_group) == 0) {
    stop("Could not create EDA-gram: insufficient finite data or sampling information.", call. = FALSE)
  }

  if (is.null(group_id_to_plot)) {
    group_id_to_plot <- names(matrix_by_group)[1]
  }

  if (!group_id_to_plot %in% names(matrix_by_group)) {
    stop("`group_id_to_plot` was not found among available groups.", call. = FALSE)
  }

  plot_matrix <- matrix_by_group[[group_id_to_plot]]

  if (isTRUE(plot)) {
    graphics::image(
      x = plot_matrix$window_midpoint,
      y = plot_matrix$frequency_hz,
      z = plot_matrix$power_matrix,
      xlab = "Time",
      ylab = "Frequency (Hz)",
      main = main
    )
  }

  overview <- data.frame(
    group_count = length(matrix_by_group),
    gram_rows = nrow(gram_table),
    plotted_group_id = group_id_to_plot,
    status = "eda_gram_created",
    interpretation = paste(
      "This is an EDA-gram-style sliding-window spectral representation.",
      "It is not a full sparse dictionary EDA-gram decomposition and does not infer emotion, stress, cognition, health status, or diagnosis."
    ),
    stringsAsFactors = FALSE
  )

  invisible(
    structure(
      list(
        overview = overview,
        gram_table = gram_table,
        plot_matrix = plot_matrix,
        settings = list(
          eda_col = eda_col,
          time_col = time_col,
          group_cols = group_cols,
          sampling_rate = sampling_rate,
          window_seconds = window_seconds,
          step_seconds = step_seconds,
          frequency_range = frequency_range,
          frequency_bins = frequency_bins,
          log_power = log_power,
          main = main
        )
      ),
      class = c("gazepoint_eda_gram", "list")
    )
  )
}

gpbiometrics_edagram_split <- function(dat, group_cols) {
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

gpbiometrics_edagram_sampling_rate <- function(time, sampling_rate = NULL) {
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

gpbiometrics_edagram_fill <- function(x) {
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
