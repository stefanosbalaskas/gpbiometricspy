
# Trial-regressor, QC-report, and all-channel preprocessing helpers

.gp_wf_check_df <- function(data, arg = "data") {
  if (!is.data.frame(data)) {
    stop("`", arg, "` must be a data frame.", call. = FALSE)
  }

  if (!nrow(data)) {
    stop("`", arg, "` has no rows.", call. = FALSE)
  }

  invisible(data)
}

.gp_wf_guess_col <- function(data, candidates, label, required = TRUE) {
  nms <- names(data)
  idx <- match(tolower(candidates), tolower(nms))
  idx <- idx[!is.na(idx)]

  if (length(idx)) {
    return(nms[idx[1L]])
  }

  if (isTRUE(required)) {
    stop("Could not identify ", label, " column. Supply it explicitly.", call. = FALSE)
  }

  NULL
}

.gp_wf_time_seconds <- function(time) {
  time <- suppressWarnings(as.numeric(time))

  if (!length(time) || all(!is.finite(time))) {
    return(seq_along(time))
  }

  d <- diff(time[is.finite(time)])
  d <- d[is.finite(d) & d > 0]

  if (!length(d)) {
    return(time)
  }

  med_d <- stats::median(d, na.rm = TRUE)

  if (is.finite(med_d) && med_d > 5) {
    time / 1000
  } else {
    time
  }
}

.gp_wf_standardize_events <- function(design,
                                      event_time_col = NULL,
                                      event_id_col = NULL) {
  if (is.numeric(design) && is.null(dim(design))) {
    return(data.frame(
      trial_id = seq_along(design),
      event_time = as.numeric(design),
      stringsAsFactors = FALSE
    ))
  }

  if (is.list(design) && !is.data.frame(design) && !is.null(design$events)) {
    design <- design$events
  }

  if (!is.data.frame(design)) {
    stop("`design` must be a numeric vector, data frame, or list with an `events` data frame.", call. = FALSE)
  }

  if (!nrow(design)) {
    stop("`design` has no rows.", call. = FALSE)
  }

  if (is.null(event_time_col)) {
    event_time_col <- .gp_wf_guess_col(
      design,
      candidates = c("event_time", "onset", "onset_time", "trial_onset", "stimulus_onset", "time_s", "time"),
      label = "event time",
      required = TRUE
    )
  }

  if (!event_time_col %in% names(design)) {
    stop("`event_time_col` not found in `design`.", call. = FALSE)
  }

  out <- design
  out$event_time <- suppressWarnings(as.numeric(out[[event_time_col]]))

  if (is.null(event_id_col)) {
    event_id_col <- .gp_wf_guess_col(
      design,
      candidates = c("trial_id", "trial", "event_id", "stimulus", "screen"),
      label = "trial/event id",
      required = FALSE
    )
  }

  if (!is.null(event_id_col) && event_id_col %in% names(out)) {
    out$trial_id <- out[[event_id_col]]
  } else {
    out$trial_id <- seq_len(nrow(out))
  }

  out
}

.gp_wf_numeric_summary <- function(x) {
  x <- suppressWarnings(as.numeric(x))

  data.frame(
    n = length(x),
    n_missing = sum(is.na(x) | !is.finite(x)),
    prop_missing = mean(is.na(x) | !is.finite(x)),
    mean = mean(x, na.rm = TRUE),
    sd = stats::sd(x, na.rm = TRUE),
    min = min(x, na.rm = TRUE),
    median = stats::median(x, na.rm = TRUE),
    max = max(x, na.rm = TRUE),
    stringsAsFactors = FALSE
  )
}

.gp_wf_escape_html <- function(x) {
  x <- as.character(x)
  x <- gsub("&", "&amp;", x, fixed = TRUE)
  x <- gsub("<", "&lt;", x, fixed = TRUE)
  x <- gsub(">", "&gt;", x, fixed = TRUE)
  x <- gsub("\"", "&quot;", x, fixed = TRUE)
  x
}

.gp_wf_table_html <- function(x, max_rows = 50) {
  if (!is.data.frame(x) || !nrow(x)) {
    return("<p>No rows.</p>")
  }

  y <- utils::head(x, max_rows)
  nms <- names(y)

  header <- paste0("<tr>", paste0("<th>", .gp_wf_escape_html(nms), "</th>", collapse = ""), "</tr>")

  rows <- apply(y, 1, function(row) {
    paste0("<tr>", paste0("<td>", .gp_wf_escape_html(row), "</td>", collapse = ""), "</tr>")
  })

  paste0(
    "<table border='1' cellspacing='0' cellpadding='4'>",
    header,
    paste(rows, collapse = "\n"),
    "</table>"
  )
}

.gp_wf_quality_one <- function(data, name = "data") {
  .gp_wf_check_df(data, arg = name)

  numeric_cols <- names(data)[vapply(data, is.numeric, logical(1))]
  all_cols <- names(data)

  miss <- data.frame(
    table = name,
    column = all_cols,
    n = nrow(data),
    n_missing = vapply(data, function(z) sum(is.na(z)), integer(1)),
    prop_missing = vapply(data, function(z) mean(is.na(z)), numeric(1)),
    stringsAsFactors = FALSE
  )

  numeric_summary <- if (length(numeric_cols)) {
    pieces <- lapply(numeric_cols, function(cc) {
      z <- .gp_wf_numeric_summary(data[[cc]])
      cbind(
        data.frame(table = name, column = cc, stringsAsFactors = FALSE),
        z
      )
    })

    do.call(rbind, pieces)
  } else {
    data.frame()
  }

  outlier_summary <- if (length(numeric_cols)) {
    pieces <- lapply(numeric_cols, function(cc) {
      x <- suppressWarnings(as.numeric(data[[cc]]))
      med <- stats::median(x, na.rm = TRUE)
      sc <- stats::mad(x, constant = 1.4826, na.rm = TRUE)

      if (!is.finite(sc) || sc == 0) {
        sc <- stats::IQR(x, na.rm = TRUE) / 1.349
      }

      flags <- if (!is.finite(sc) || sc == 0) {
        rep(FALSE, length(x))
      } else {
        abs(x - med) > 5 * sc
      }

      flags[is.na(flags)] <- FALSE

      data.frame(
        table = name,
        column = cc,
        n_outlier_mad5 = sum(flags, na.rm = TRUE),
        prop_outlier_mad5 = mean(flags, na.rm = TRUE),
        stringsAsFactors = FALSE
      )
    })

    do.call(rbind, pieces)
  } else {
    data.frame()
  }

  list(
    missingness = miss,
    numeric_summary = numeric_summary,
    outlier_summary = outlier_summary
  )
}

.gp_wf_find_signal_table <- function(data, patterns) {
  if (is.data.frame(data)) {
    return(data)
  }

  if (!is.list(data)) {
    stop("`data` must be a data frame or list of data frames.", call. = FALSE)
  }

  nms <- names(data)

  if (is.null(nms)) {
    nms <- rep("", length(data))
  }

  for (pat in patterns) {
    hit <- which(grepl(pat, nms, ignore.case = TRUE))

    if (length(hit) && is.data.frame(data[[hit[1L]]])) {
      return(data[[hit[1L]]])
    }
  }

  for (i in seq_along(data)) {
    if (is.data.frame(data[[i]])) {
      cols <- names(data[[i]])
      if (any(grepl(paste(patterns, collapse = "|"), cols, ignore.case = TRUE))) {
        return(data[[i]])
      }
    }
  }

  NULL
}

.gp_wf_safe_call <- function(expr) {
  tryCatch(
    list(result = eval.parent(substitute(expr)), error = NULL),
    error = function(e) list(result = NULL, error = conditionMessage(e))
  )
}

#' Create Gazepoint trial-level regressors for modeling
#'
#' Prepares a long-format trial table by joining stimulus/event design
#' information with event-window summaries from numeric Gazepoint channels.
#' The output is intended for downstream GLM, LMM, or mixed-model workflows.
#'
#' @param data Data frame containing time-series signals, or a list of data
#'   frames.
#' @param design Numeric event timestamps, a design data frame, or a list with
#'   an `events` data frame.
#' @param pre Seconds before event onset to summarize.
#' @param post Seconds after event onset to summarize.
#' @param time_col Time column in `data`.
#' @param event_time_col Event-time column in `design`.
#' @param event_id_col Trial/event identifier column in `design`.
#' @param signal_cols Numeric signal columns to summarize. If NULL, all numeric
#'   columns except the time column are used.
#' @param subject_col Optional subject/participant column in `data`.
#' @param design_subject_col Optional subject/participant column in `design`.
#' @param carry_design_cols Design columns to carry into the output. If NULL,
#'   all non-time design columns are carried.
#'
#' @return A data frame with one row per trial/event and signal summary
#'   regressors.
#' @export
#'
#' @examples
#' dat <- data.frame(time_s = seq(0, 10, by = 1), GSR = seq(0, 1, length.out = 11))
#' design <- data.frame(trial = "T1", onset = 5, condition = "A")
#' create_gazepoint_trial_regressors(dat, design, pre = 1, post = 2)
create_gazepoint_trial_regressors <- function(data,
                                              design,
                                              pre = 0,
                                              post = 5,
                                              time_col = NULL,
                                              event_time_col = NULL,
                                              event_id_col = NULL,
                                              signal_cols = NULL,
                                              subject_col = NULL,
                                              design_subject_col = NULL,
                                              carry_design_cols = NULL) {
  if (is.list(data) && !is.data.frame(data)) {
    data <- .gp_wf_find_signal_table(data, patterns = c("biometric", "all_gaze", "gaze", "signal", "data"))
  }

  .gp_wf_check_df(data)

  if (missing(design)) {
    stop("Supply `design` as event timestamps, a design data frame, or a list with `events`.", call. = FALSE)
  }

  if (!is.numeric(pre) || !is.numeric(post) || pre < 0 || post <= 0) {
    stop("`pre` must be non-negative and `post` must be positive.", call. = FALSE)
  }

  time_col <- if (is.null(time_col)) {
    .gp_wf_guess_col(
      data,
      candidates = c("time_s", "time", "TIME", "timestamp", "MSTIMER"),
      label = "time",
      required = TRUE
    )
  } else {
    time_col
  }

  if (!time_col %in% names(data)) {
    stop("`time_col` not found in `data`.", call. = FALSE)
  }

  events <- .gp_wf_standardize_events(
    design = design,
    event_time_col = event_time_col,
    event_id_col = event_id_col
  )

  if (is.null(signal_cols)) {
    numeric_cols <- names(data)[vapply(data, is.numeric, logical(1))]
    signal_cols <- setdiff(numeric_cols, time_col)
  }

  if (!length(signal_cols)) {
    stop("No numeric `signal_cols` available for trial summaries.", call. = FALSE)
  }

  missing_signals <- setdiff(signal_cols, names(data))
  if (length(missing_signals)) {
    stop("Missing signal columns: ", paste(missing_signals, collapse = ", "), call. = FALSE)
  }

  if (!is.null(subject_col) && !subject_col %in% names(data)) {
    stop("`subject_col` not found in `data`.", call. = FALSE)
  }

  if (!is.null(design_subject_col) && !design_subject_col %in% names(events)) {
    stop("`design_subject_col` not found in `design`.", call. = FALSE)
  }

  if (is.null(carry_design_cols)) {
    carry_design_cols <- setdiff(names(events), "event_time")
  }

  carry_design_cols <- intersect(carry_design_cols, names(events))

  time <- .gp_wf_time_seconds(data[[time_col]])
  rows <- vector("list", nrow(events))

  for (i in seq_len(nrow(events))) {
    event_time <- as.numeric(events$event_time[i])
    idx <- which(time >= event_time - pre & time <= event_time + post)

    if (!is.null(subject_col) && !is.null(design_subject_col)) {
      idx <- idx[data[[subject_col]][idx] == events[[design_subject_col]][i]]
    }

    row <- events[i, carry_design_cols, drop = FALSE]
    row$event_time <- event_time
    row$pre <- pre
    row$post <- post
    row$n_samples <- length(idx)

    for (cc in signal_cols) {
      x <- suppressWarnings(as.numeric(data[[cc]][idx]))

      row[[paste0(cc, "_mean")]] <- mean(x, na.rm = TRUE)
      row[[paste0(cc, "_sd")]] <- stats::sd(x, na.rm = TRUE)
      row[[paste0(cc, "_min")]] <- min(x, na.rm = TRUE)
      row[[paste0(cc, "_max")]] <- max(x, na.rm = TRUE)
      row[[paste0(cc, "_range")]] <- diff(range(x, na.rm = TRUE))
      row[[paste0(cc, "_missing_prop")]] <- if (length(x)) mean(is.na(x) | !is.finite(x)) else NA_real_
    }

    rows[[i]] <- row
  }

  out <- do.call(rbind, rows)
  row.names(out) <- NULL

  attr(out, "time_col") <- time_col
  attr(out, "signal_cols") <- signal_cols

  out
}

#' Report Gazepoint data quality
#'
#' Generates dependency-free data-quality report files for Gazepoint data. The
#' report summarizes missingness, numeric distributions, robust outlier counts,
#' and simple QC plots. HTML and PDF outputs are created using base R only.
#'
#' @param data Data frame or list of data frames.
#' @param output_dir Output directory.
#' @param report_name File prefix for report outputs.
#' @param formats Character vector containing `"html"`, `"pdf"`, and/or
#'   `"csv"`.
#' @param max_plot_columns Maximum number of numeric columns plotted per table.
#' @param open If TRUE, open the HTML report interactively.
#'
#' @return Invisibly returns a list with output paths and summary tables.
#' @export
#'
#' @examples
#' \dontrun{
#' report_gazepoint_data_quality(data.frame(time_s = 1:5, GSR = rnorm(5)))
#' }
report_gazepoint_data_quality <- function(data,
                                          output_dir = tempfile("gazepoint_quality_report_"),
                                          report_name = "gazepoint_data_quality",
                                          formats = c("html", "csv"),
                                          max_plot_columns = 6,
                                          open = FALSE) {
  if (!dir.exists(output_dir)) {
    dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
  }

  if (is.data.frame(data)) {
    data_list <- list(data = data)
  } else if (is.list(data)) {
    data_list <- data[vapply(data, is.data.frame, logical(1))]

    if (!length(data_list)) {
      stop("`data` list does not contain any data frames.", call. = FALSE)
    }

    if (is.null(names(data_list)) || any(!nzchar(names(data_list)))) {
      names(data_list) <- paste0("table_", seq_along(data_list))
    }
  } else {
    stop("`data` must be a data frame or list of data frames.", call. = FALSE)
  }

  qc <- lapply(names(data_list), function(nm) .gp_wf_quality_one(data_list[[nm]], name = nm))
  names(qc) <- names(data_list)

  missingness <- do.call(rbind, lapply(qc, `[[`, "missingness"))
  numeric_summary <- do.call(rbind, lapply(qc, `[[`, "numeric_summary"))
  outlier_summary <- do.call(rbind, lapply(qc, `[[`, "outlier_summary"))

  paths <- list()

  if ("csv" %in% formats) {
    paths$missingness_csv <- file.path(output_dir, paste0(report_name, "_missingness.csv"))
    paths$numeric_summary_csv <- file.path(output_dir, paste0(report_name, "_numeric_summary.csv"))
    paths$outlier_summary_csv <- file.path(output_dir, paste0(report_name, "_outlier_summary.csv"))

    utils::write.csv(missingness, paths$missingness_csv, row.names = FALSE)
    utils::write.csv(numeric_summary, paths$numeric_summary_csv, row.names = FALSE)
    utils::write.csv(outlier_summary, paths$outlier_summary_csv, row.names = FALSE)
  }

  if ("html" %in% formats) {
    paths$html <- file.path(output_dir, paste0(report_name, ".html"))

    html <- c(
      "<!doctype html>",
      "<html><head><meta charset='utf-8'>",
      "<title>Gazepoint data quality report</title>",
      "<style>body{font-family:Arial,sans-serif;max-width:1100px;margin:2em auto;line-height:1.45;} table{border-collapse:collapse;margin-bottom:1.5em;} th{background:#f2f2f2;} td,th{font-size:12px;} code{background:#f7f7f7;padding:2px 4px;}</style>",
      "</head><body>",
      "<h1>Gazepoint data quality report</h1>",
      paste0("<p><strong>Generated:</strong> ", .gp_wf_escape_html(Sys.time()), "</p>"),
      paste0("<p><strong>Tables:</strong> ", paste(.gp_wf_escape_html(names(data_list)), collapse = ", "), "</p>"),
      "<h2>Missingness</h2>",
      .gp_wf_table_html(missingness),
      "<h2>Numeric summary</h2>",
      .gp_wf_table_html(numeric_summary),
      "<h2>Robust outlier summary</h2>",
      .gp_wf_table_html(outlier_summary),
      "</body></html>"
    )

    writeLines(html, paths$html, useBytes = TRUE)

    if (isTRUE(open)) {
      utils::browseURL(paths$html)
    }
  }

  if ("pdf" %in% formats) {
    paths$pdf <- file.path(output_dir, paste0(report_name, "_plots.pdf"))

    grDevices::pdf(paths$pdf, width = 10, height = 7)
    on.exit(grDevices::dev.off(), add = TRUE)

    for (nm in names(data_list)) {
      dat <- data_list[[nm]]
      numeric_cols <- names(dat)[vapply(dat, is.numeric, logical(1))]
      numeric_cols <- utils::head(numeric_cols, max_plot_columns)

      if (!length(numeric_cols)) {
        graphics::plot.new()
        graphics::title(main = paste("No numeric columns:", nm))
      } else {
        old_par <- graphics::par(no.readonly = TRUE)
        on.exit(graphics::par(old_par), add = TRUE)
        graphics::par(mfrow = c(ceiling(length(numeric_cols) / 2), 2))

        for (cc in numeric_cols) {
          x <- suppressWarnings(as.numeric(dat[[cc]]))
          graphics::hist(
            x,
            main = paste(nm, cc),
            xlab = cc,
            col = "gray",
            border = "white"
          )
        }
      }
    }

    grDevices::dev.off()
  }

  result <- list(
    output_dir = normalizePath(output_dir, winslash = "/", mustWork = FALSE),
    paths = paths,
    missingness = missingness,
    numeric_summary = numeric_summary,
    outlier_summary = outlier_summary
  )

  invisible(result)
}

#' Preprocess all available Gazepoint channels
#'
#' Runs a conservative, beginner-friendly preprocessing sequence over a
#' Gazepoint data frame or imported session list. Available channels are
#' detected heuristically. Missing numeric signal gaps can be imputed, pupil
#' blinks cleaned, and gaze samples filtered when the relevant functions and
#' columns are available.
#'
#' @param data Data frame or list of data frames.
#' @param impute_missing If TRUE, impute short missing gaps in numeric columns.
#' @param clean_pupil If TRUE, clean detected pupil columns.
#' @param filter_gaze If TRUE, filter detected gaze coordinates.
#' @param max_gap Maximum gap length in samples for imputation.
#' @param screen_bounds Screen bounds for gaze filtering.
#' @param max_velocity Maximum gaze velocity for gaze filtering.
#' @param verbose If TRUE, print a compact preprocessing log.
#'
#' @return A preprocessed object of the same basic structure as `data`, with a
#'   `preprocessing_log` attribute.
#' @export
#'
#' @examples
#' dat <- data.frame(time_s = 1:5, GSR = c(1, NA, 3, 4, 5))
#' preprocess_gazepoint_all(dat)
preprocess_gazepoint_all <- function(data,
                                     impute_missing = TRUE,
                                     clean_pupil = TRUE,
                                     filter_gaze = TRUE,
                                     max_gap = 10,
                                     screen_bounds = c(0, 1, 0, 1),
                                     max_velocity = Inf,
                                     verbose = TRUE) {
  process_one <- function(dat, name = "data") {
    .gp_wf_check_df(dat, arg = name)

    log <- data.frame(
      table = character(),
      step = character(),
      status = character(),
      message = character(),
      stringsAsFactors = FALSE
    )

    add_log <- function(step, status, message = "") {
      log <<- rbind(
        log,
        data.frame(
          table = name,
          step = step,
          status = status,
          message = message,
          stringsAsFactors = FALSE
        )
      )
    }

    out <- dat

    if (isTRUE(impute_missing)) {
      numeric_cols <- names(out)[vapply(out, is.numeric, logical(1))]
      time_col <- .gp_wf_guess_col(out, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", required = FALSE)
      numeric_cols <- setdiff(numeric_cols, time_col)

      if (length(numeric_cols)) {
        res <- .gp_wf_safe_call(
          impute_gazepoint_missing(
            out,
            cols = numeric_cols,
            time_col = time_col,
            max_gap = max_gap,
            add_flags = TRUE
          )
        )

        if (is.null(res$error)) {
          out <- res$result
          add_log("impute_missing", "ok", paste("Columns:", paste(numeric_cols, collapse = ", ")))
        } else {
          add_log("impute_missing", "skipped", res$error)
        }
      } else {
        add_log("impute_missing", "skipped", "No numeric columns.")
      }
    }

    if (isTRUE(clean_pupil)) {
      has_pupil <- any(grepl("pupil|^LPD$|^RPD$", names(out), ignore.case = TRUE))

      if (has_pupil && exists("clean_gazepoint_pupil_signal", mode = "function")) {
        time_col <- .gp_wf_guess_col(out, c("time_s", "time", "TIME", "timestamp", "MSTIMER"), "time", required = FALSE)

        res <- .gp_wf_safe_call(
          clean_gazepoint_pupil_signal(
            out,
            time_col = time_col,
            max_gap = max_gap
          )
        )

        if (is.null(res$error)) {
          out <- res$result
          add_log("clean_pupil", "ok", "Pupil columns cleaned.")
        } else {
          add_log("clean_pupil", "skipped", res$error)
        }
      } else {
        add_log("clean_pupil", "skipped", "No pupil columns or cleaner unavailable.")
      }
    }

    if (isTRUE(filter_gaze)) {
      has_gaze <- any(tolower(names(out)) %in% tolower(c("BPOGX", "FPOGX", "GPOGX", "x", "gaze_x"))) &&
        any(tolower(names(out)) %in% tolower(c("BPOGY", "FPOGY", "GPOGY", "y", "gaze_y")))

      if (has_gaze && exists("filter_gazepoint_gaze", mode = "function")) {
        res <- .gp_wf_safe_call(
          filter_gazepoint_gaze(
            out,
            screen_bounds = screen_bounds,
            max_velocity = max_velocity
          )
        )

        if (is.null(res$error)) {
          out <- res$result
          add_log("filter_gaze", "ok", "Gaze coordinates filtered.")
        } else {
          add_log("filter_gaze", "skipped", res$error)
        }
      } else {
        add_log("filter_gaze", "skipped", "No gaze coordinate columns or filter unavailable.")
      }
    }

    attr(out, "preprocessing_log") <- log
    out
  }

  if (is.data.frame(data)) {
    out <- process_one(data, name = "data")
    log <- attr(out, "preprocessing_log")
  } else if (is.list(data)) {
    data_frames <- vapply(data, is.data.frame, logical(1))
    out <- data

    if (is.null(names(out)) || any(!nzchar(names(out)))) {
      names(out) <- paste0("table_", seq_along(out))
    }

    logs <- list()

    for (nm in names(out)[data_frames]) {
      out[[nm]] <- process_one(out[[nm]], name = nm)
      logs[[nm]] <- attr(out[[nm]], "preprocessing_log")
    }

    log <- do.call(rbind, logs)
    attr(out, "preprocessing_log") <- log
  } else {
    stop("`data` must be a data frame or list of data frames.", call. = FALSE)
  }

  if (isTRUE(verbose)) {
    print(log)
  }

  out
}

