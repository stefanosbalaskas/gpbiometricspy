#' Plot Gazepoint biometric signal time series
#'
#' Plots one or more Gazepoint biometric signals using base R graphics and
#' returns the plotted data and signal summary. The helper is intentionally
#' descriptive and does not infer emotional valence, cognition, or HRV from raw
#' biometric columns.
#'
#' @param data A data frame.
#' @param signal_cols Optional character vector of signal columns. If `NULL`,
#'   common Gazepoint biometric signal columns are detected.
#' @param time_col Optional time/order column for the x-axis. If `NULL`, row
#'   number is used.
#' @param group_col Optional grouping column recorded in the returned overview.
#'   The current plotting implementation overlays the selected rows rather than
#'   faceting by group.
#' @param max_points Maximum number of rows to plot. Large data are evenly
#'   downsampled for display only; returned summaries still describe the input
#'   signal columns.
#' @param standardize Logical. Should each signal be z-standardised before
#'   plotting? This is useful when signals are on different scales.
#' @param type Plot type: `"line"`, `"points"`, or `"both"`.
#' @param main Optional plot title.
#' @param xlab Optional x-axis label.
#' @param ylab Optional y-axis label.
#' @param legend Logical. Should a legend be drawn when more than one signal is
#'   plotted?
#' @param plot Logical. If `FALSE`, no plot is drawn and only the plot object is
#'   returned.
#' @param ... Additional arguments passed to [matplot()].
#'
#' @return A list with `overview`, `plot_data`, `signal_summary`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:5,
#'   GSR = c(1, 1.1, 1.2, 1.1, 1),
#'   HR = c(70, 71, 72, 71, 70)
#' )
#' plot_gazepoint_biometric_signals(df, time_col = "CNT", plot = FALSE)
#'
#' @export
plot_gazepoint_biometric_signals <- function(data,
                                             signal_cols = NULL,
                                             time_col = NULL,
                                             group_col = NULL,
                                             max_points = 5000L,
                                             standardize = FALSE,
                                             type = c("line", "points", "both"),
                                             main = NULL,
                                             xlab = NULL,
                                             ylab = NULL,
                                             legend = TRUE,
                                             plot = TRUE,
                                             ...) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  type <- match.arg(type)

  if (!is.null(signal_cols)) {
    .gpbiom_assert_columns(data, signal_cols, "signal_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
    if (length(time_col) != 1L) {
      stop("`time_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(group_col)) {
    .gpbiom_assert_columns(data, group_col, "group_col")
    if (length(group_col) != 1L) {
      stop("`group_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  .gpbiom_assert_positive_integer(max_points, "max_points")

  if (!is.logical(standardize) ||
      length(standardize) != 1L ||
      is.na(standardize)) {
    stop("`standardize` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(legend) || length(legend) != 1L || is.na(legend)) {
    stop("`legend` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(plot) || length(plot) != 1L || is.na(plot)) {
    stop("`plot` must be TRUE or FALSE.", call. = FALSE)
  }

  if (is.null(signal_cols)) {
    signal_cols <- .gpbiom_detect_signal_columns(data)
  }

  if (length(signal_cols) == 0L) {
    stop("No biometric signal columns were detected. Provide `signal_cols` explicitly.",
         call. = FALSE)
  }

  non_numeric <- signal_cols[!vapply(signal_cols, function(column) {
    is.numeric(data[[column]])
  }, logical(1))]

  if (length(non_numeric) > 0L) {
    stop(
      "All selected `signal_cols` must be numeric. Non-numeric columns: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  order_index <- .gpbiom_plot_order_index(data, time_col)
  plot_index <- .gpbiom_plot_downsample_index(order_index, max_points)

  x <- if (is.null(time_col)) {
    seq_len(nrow(data))[plot_index]
  } else {
    data[[time_col]][plot_index]
  }

  signal_matrix <- as.matrix(data[plot_index, signal_cols, drop = FALSE])

  if (isTRUE(standardize)) {
    signal_matrix <- .gpbiom_plot_standardize_matrix(signal_matrix)
  }

  plot_data <- data.frame(
    .row_id = plot_index,
    .x = x,
    signal_matrix,
    check.names = FALSE
  )

  signal_summary <- .gpbiom_summarise_signal_columns(
    data = data,
    signal_cols = signal_cols,
    active_min_unique = 2L
  )

  overview <- data.frame(
    n_rows = nrow(data),
    plotted_rows = nrow(plot_data),
    signal_column_count = length(signal_cols),
    time_col = ifelse(is.null(time_col), NA_character_, time_col),
    group_col = ifelse(is.null(group_col), NA_character_, group_col),
    group_count = .gpbiom_plot_group_count(data, group_col),
    standardize = standardize,
    plot_created = plot,
    status = if (nrow(plot_data) == 0L) {
      "no_rows_to_plot"
    } else {
      "signal_plot_prepared"
    },
    stringsAsFactors = FALSE
  )

  if (isTRUE(plot)) {
    plot_type <- switch(
      type,
      line = "l",
      points = "p",
      both = "b"
    )

    plot_main <- if (is.null(main)) {
      "Gazepoint biometric signals"
    } else {
      main
    }

    plot_xlab <- if (is.null(xlab)) {
      if (is.null(time_col)) "Row" else time_col
    } else {
      xlab
    }

    plot_ylab <- if (is.null(ylab)) {
      if (isTRUE(standardize)) "Standardised signal" else "Signal value"
    } else {
      ylab
    }

    graphics::matplot(
      x = plot_data$.x,
      y = as.matrix(plot_data[signal_cols]),
      type = plot_type,
      lty = 1,
      pch = 1,
      xlab = plot_xlab,
      ylab = plot_ylab,
      main = plot_main,
      ...
    )

    if (isTRUE(legend) && length(signal_cols) > 1L) {
      graphics::legend(
        "topright",
        legend = signal_cols,
        col = seq_along(signal_cols),
        lty = 1,
        pch = 1,
        bty = "n"
      )
    }
  }

  out <- list(
    overview = overview,
    plot_data = plot_data,
    signal_summary = signal_summary,
    settings = list(
      signal_cols = signal_cols,
      time_col = time_col,
      group_col = group_col,
      max_points = as.integer(max_points),
      standardize = standardize,
      type = type,
      note = paste0(
        "Signal plots describe biometric time-series patterns only; they do ",
        "not establish emotional valence, cognition, or HRV."
      )
    )
  )

  class(out) <- c("gazepoint_biometric_signal_plot", class(out))
  out
}


#' Plot Gazepoint biometric quality indicators
#'
#' Plots and summarises biometric quality indicators such as dropout flags,
#' validity flags, missingness flags, and quality/audit flags. When no explicit
#' quality columns are available, the function can derive missingness indicators
#' from detected biometric signal columns.
#'
#' @param data A data frame.
#' @param quality_cols Optional quality/flag columns. If `NULL`, likely quality
#'   columns are detected from names and types.
#' @param signal_cols Optional signal columns used to derive missingness flags
#'   when no quality columns are detected.
#' @param time_col Optional time/order column recorded in the returned settings.
#' @param group_col Optional grouping column for group-level quality summaries.
#' @param dropout_prefix Prefix used by dropout columns created by
#'   [flag_gazepoint_biometric_dropouts()].
#' @param max_points Maximum number of rows used for row-level returned plot
#'   data.
#' @param main Optional plot title.
#' @param plot Logical. If `FALSE`, no plot is drawn.
#' @param ... Additional arguments passed to [barplot()].
#'
#' @return A list with `overview`, `quality_summary`, `group_summary`,
#'   `plot_data`, and `settings`.
#'
#' @examples
#' df <- data.frame(
#'   CNT = 1:5,
#'   GSR = c(1, NA, 1.2, 1.1, NA),
#'   HR_valid = c(1, 1, 0, 1, 1)
#' )
#' plot_gazepoint_biometric_quality(df, signal_cols = "GSR", plot = FALSE)
#'
#' @export
plot_gazepoint_biometric_quality <- function(data,
                                             quality_cols = NULL,
                                             signal_cols = NULL,
                                             time_col = NULL,
                                             group_col = NULL,
                                             dropout_prefix = "biometric_dropout",
                                             max_points = 5000L,
                                             main = NULL,
                                             plot = TRUE,
                                             ...) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.null(quality_cols)) {
    .gpbiom_assert_columns(data, quality_cols, "quality_cols")
  }

  if (!is.null(signal_cols)) {
    .gpbiom_assert_columns(data, signal_cols, "signal_cols")
  }

  if (!is.null(time_col)) {
    .gpbiom_assert_columns(data, time_col, "time_col")
    if (length(time_col) != 1L) {
      stop("`time_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.null(group_col)) {
    .gpbiom_assert_columns(data, group_col, "group_col")
    if (length(group_col) != 1L) {
      stop("`group_col` must be NULL or a single column name.", call. = FALSE)
    }
  }

  if (!is.character(dropout_prefix) ||
      length(dropout_prefix) != 1L ||
      is.na(dropout_prefix) ||
      !nzchar(dropout_prefix)) {
    stop("`dropout_prefix` must be a non-empty character string.",
         call. = FALSE)
  }

  .gpbiom_assert_positive_integer(max_points, "max_points")

  if (!is.logical(plot) || length(plot) != 1L || is.na(plot)) {
    stop("`plot` must be TRUE or FALSE.", call. = FALSE)
  }

  if (is.null(quality_cols)) {
    quality_cols <- .gpbiom_detect_quality_columns(data, dropout_prefix)
  }

  derived_from_signals <- FALSE

  if (length(quality_cols) == 0L) {
    if (is.null(signal_cols)) {
      signal_cols <- .gpbiom_detect_signal_columns(data)
    }

    if (length(signal_cols) == 0L) {
      stop("No quality columns or signal columns were detected.",
           call. = FALSE)
    }

    quality_data <- .gpbiom_derive_missingness_quality_data(data, signal_cols)
    quality_cols <- names(quality_data)
    derived_from_signals <- TRUE
  } else {
    quality_data <- data[quality_cols]
  }

  quality_summary <- .gpbiom_quality_summary(
    quality_data = quality_data,
    original_names = quality_cols,
    derived_from_signals = derived_from_signals
  )

  group_summary <- .gpbiom_quality_group_summary(
    data = data,
    quality_data = quality_data,
    group_col = group_col,
    derived_from_signals = derived_from_signals
  )

  order_index <- .gpbiom_plot_order_index(data, time_col)
  plot_index <- .gpbiom_plot_downsample_index(order_index, max_points)

  plot_data <- data.frame(
    .row_id = plot_index,
    quality_data[plot_index, , drop = FALSE],
    check.names = FALSE
  )

  overview <- data.frame(
    n_rows = nrow(data),
    plotted_rows = nrow(plot_data),
    quality_column_count = length(quality_cols),
    group_col = ifelse(is.null(group_col), NA_character_, group_col),
    group_count = .gpbiom_plot_group_count(data, group_col),
    derived_from_signals = derived_from_signals,
    plot_created = plot,
    status = if (nrow(quality_summary) == 0L) {
      "no_quality_summary"
    } else if (any(quality_summary$flag_rate > 0, na.rm = TRUE)) {
      "quality_flags_present"
    } else {
      "no_quality_flags_present"
    },
    stringsAsFactors = FALSE
  )

  if (isTRUE(plot)) {
    plot_main <- if (is.null(main)) {
      "Gazepoint biometric quality indicators"
    } else {
      main
    }

    heights <- quality_summary$flag_rate
    names(heights) <- quality_summary$column

    graphics::barplot(
      heights,
      ylim = c(0, 1),
      ylab = "Flag rate",
      main = plot_main,
      las = 2,
      ...
    )
  }

  out <- list(
    overview = overview,
    quality_summary = quality_summary,
    group_summary = group_summary,
    plot_data = plot_data,
    settings = list(
      quality_cols = quality_cols,
      signal_cols = signal_cols,
      time_col = time_col,
      group_col = group_col,
      dropout_prefix = dropout_prefix,
      max_points = as.integer(max_points),
      derived_from_signals = derived_from_signals,
      note = paste0(
        "Quality plots summarise availability, validity, dropout, or ",
        "missingness indicators; they are not physiological interpretations."
      )
    )
  )

  class(out) <- c("gazepoint_biometric_quality_plot", class(out))
  out
}


.gpbiom_plot_order_index <- function(data, time_col) {
  index <- seq_len(nrow(data))

  if (is.null(time_col)) {
    return(index)
  }

  index[order(data[[time_col]], na.last = TRUE)]
}


.gpbiom_plot_downsample_index <- function(index, max_points) {
  if (length(index) <= max_points) {
    return(index)
  }

  index[unique(round(seq(1, length(index), length.out = max_points)))]
}


.gpbiom_plot_standardize_matrix <- function(x) {
  out <- x

  for (j in seq_len(ncol(out))) {
    values <- out[, j]
    finite <- values[!is.na(values) & is.finite(values)]

    if (length(finite) == 0L) {
      out[, j] <- NA_real_
      next
    }

    center <- mean(finite)
    scale <- stats::sd(finite)

    if (!is.finite(scale) || scale == 0) {
      out[, j] <- values - center
    } else {
      out[, j] <- (values - center) / scale
    }
  }

  out
}


.gpbiom_plot_group_count <- function(data, group_col) {
  if (is.null(group_col)) {
    return(NA_integer_)
  }

  length(unique(data[[group_col]][!is.na(data[[group_col]])]))
}


.gpbiom_detect_quality_columns <- function(data, dropout_prefix) {
  column_names <- names(data)
  cleaned <- .gpbiom_clean_name(column_names)

  quality_name <- grepl(
    paste0(
      "dropout|valid|validity|quality|flag|artifact|artefact|",
      "missing|nonfinite|excluded|exclude|", dropout_prefix
    ),
    cleaned,
    ignore.case = TRUE
  )

  usable_type <- vapply(data, function(column) {
    is.logical(column) || is.numeric(column) || is.character(column) ||
      is.factor(column)
  }, logical(1))

  column_names[quality_name & usable_type]
}


.gpbiom_derive_missingness_quality_data <- function(data, signal_cols) {
  out <- data.frame(row.names = seq_len(nrow(data)))

  for (signal in signal_cols) {
    safe <- .gpbiom_safe_colname(signal)
    values <- data[[signal]]

    flags <- is.na(values)

    if (is.numeric(values)) {
      flags <- flags | !is.finite(values)
    }

    out[[paste0(safe, "_missing")]] <- flags
  }

  out
}


.gpbiom_quality_summary <- function(quality_data,
                                    original_names,
                                    derived_from_signals) {
  if (length(original_names) == 0L || ncol(quality_data) == 0L) {
    return(data.frame(
      column = character(),
      n = integer(),
      n_flagged = integer(),
      flag_rate = numeric(),
      n_missing = integer(),
      missing_rate = numeric(),
      source = character(),
      stringsAsFactors = FALSE
    ))
  }

  rows <- lapply(seq_along(original_names), function(i) {
    column <- names(quality_data)[i]
    values <- quality_data[[i]]
    flags <- .gpbiom_quality_flag_vector(values, column)

    data.frame(
      column = original_names[i],
      n = length(values),
      n_flagged = sum(flags, na.rm = TRUE),
      flag_rate = if (length(values) > 0L) mean(flags, na.rm = TRUE) else NA_real_,
      n_missing = sum(is.na(values)),
      missing_rate = if (length(values) > 0L) mean(is.na(values)) else NA_real_,
      source = if (isTRUE(derived_from_signals)) {
        "derived_signal_missingness"
      } else {
        "quality_column"
      },
      stringsAsFactors = FALSE
    )
  })

  do.call(rbind, rows)
}


.gpbiom_quality_group_summary <- function(data,
                                          quality_data,
                                          group_col,
                                          derived_from_signals) {
  if (is.null(group_col)) {
    return(data.frame(
      group = character(),
      column = character(),
      n = integer(),
      n_flagged = integer(),
      flag_rate = numeric(),
      source = character(),
      stringsAsFactors = FALSE
    ))
  }

  groups <- split(seq_len(nrow(data)), data[[group_col]], drop = TRUE)

  rows <- list()

  for (group_name in names(groups)) {
    index <- groups[[group_name]]

    for (column in names(quality_data)) {
      values <- quality_data[[column]][index]
      flags <- .gpbiom_quality_flag_vector(values, column)

      rows[[length(rows) + 1L]] <- data.frame(
        group = group_name,
        column = column,
        n = length(values),
        n_flagged = sum(flags, na.rm = TRUE),
        flag_rate = if (length(values) > 0L) mean(flags, na.rm = TRUE) else NA_real_,
        source = if (isTRUE(derived_from_signals)) {
          "derived_signal_missingness"
        } else {
          "quality_column"
        },
        stringsAsFactors = FALSE
      )
    }
  }

  if (length(rows) == 0L) {
    return(data.frame(
      group = character(),
      column = character(),
      n = integer(),
      n_flagged = integer(),
      flag_rate = numeric(),
      source = character(),
      stringsAsFactors = FALSE
    ))
  }

  do.call(rbind, rows)
}


.gpbiom_quality_flag_vector <- function(values, column_name) {
  name <- tolower(column_name)

  if (is.logical(values)) {
    return(!is.na(values) & values)
  }

  if (is.numeric(values)) {
    if (grepl("valid", name) && !grepl("invalid", name)) {
      return(!is.na(values) & is.finite(values) & values <= 0)
    }

    return(!is.na(values) & is.finite(values) & values != 0)
  }

  cleaned <- tolower(trimws(as.character(values)))

  if (grepl("valid", name) && !grepl("invalid", name)) {
    return(!is.na(values) & cleaned %in% c(
      "0", "false", "invalid", "no", "n", "bad", "fail", "failed"
    ))
  }

  !is.na(values) & cleaned %in% c(
    "1", "true", "yes", "y", "flag", "flagged", "bad", "fail",
    "failed", "invalid", "artifact", "artefact", "missing", "exclude",
    "excluded"
  )
}
