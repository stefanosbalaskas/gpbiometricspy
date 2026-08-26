#' Prepare EDA artifact-classifier segment features
#'
#' Creates segment-level features that can be passed to a user-supplied
#' artifact classifier such as an SVM. No pretrained classifier is bundled.
#'
#' @param dat A data frame.
#' @param eda_col EDA/conductance column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param segment_seconds Segment length in seconds when `time_col` is supplied.
#' @param samples_per_segment Segment length in samples when no usable time
#'   column or sampling rate is available.
#' @param sampling_rate Optional sampling rate in Hz.
#'
#' @return A segment-level feature data frame.
#' @export
prepare_gazepoint_artifact_svm_features <- function(dat,
                                                    eda_col = "GSR_US",
                                                    time_col = NULL,
                                                    group_cols = NULL,
                                                    segment_seconds = 5,
                                                    samples_per_segment = NULL,
                                                    sampling_rate = NULL) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!eda_col %in% names(dat)) {
    stop("Column `", eda_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[eda_col]])) {
    stop("`eda_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("Column `", time_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_svm_split(dat, group_cols)

  rows <- list()
  row_id <- 1L

  for (group_id in names(groups)) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(dat[[time_col]][idx])]
    }

    x <- dat[[eda_col]][idx]

    fs <- if (!is.null(time_col)) {
      gpbiometrics_svm_sampling_rate(dat[[time_col]][idx], sampling_rate)
    } else {
      sampling_rate
    }

    n_per_segment <- if (!is.null(samples_per_segment)) {
      samples_per_segment
    } else if (is.finite(fs) && fs > 0) {
      max(2, round(segment_seconds * fs))
    } else {
      5
    }

    starts <- seq(1, length(idx), by = n_per_segment)

    for (seg_i in seq_along(starts)) {
      seg_idx_local <- starts[seg_i]:min(starts[seg_i] + n_per_segment - 1, length(idx))
      seg_idx <- idx[seg_idx_local]
      seg_x <- dat[[eda_col]][seg_idx]
      finite_x <- seg_x[is.finite(seg_x)]

      if (length(finite_x) < 2) {
        status <- "insufficient_segment_data"
        feat <- rep(NA_real_, 10)
        names(feat) <- c(
          "mean_signal", "sd_signal", "min_signal", "max_signal", "range_signal",
          "median_abs_diff", "max_abs_diff", "slope", "zero_crossing_diff",
          "detail_energy"
        )
      } else {
        d <- diff(finite_x)
        tt <- seq_along(finite_x)
        slope <- tryCatch(stats::coef(stats::lm(finite_x ~ tt))[2], error = function(e) NA_real_)
        detail <- gpbiometrics_svm_detail_energy(finite_x)

        feat <- c(
          mean_signal = mean(finite_x),
          sd_signal = stats::sd(finite_x),
          min_signal = min(finite_x),
          max_signal = max(finite_x),
          range_signal = diff(range(finite_x)),
          median_abs_diff = stats::median(abs(d)),
          max_abs_diff = max(abs(d)),
          slope = unname(slope),
          zero_crossing_diff = sum(diff(sign(d - mean(d))) != 0, na.rm = TRUE),
          detail_energy = detail
        )
        status <- "svm_features_prepared"
      }

      time_start <- if (!is.null(time_col)) dat[[time_col]][seg_idx[1]] else NA_real_
      time_end <- if (!is.null(time_col)) dat[[time_col]][seg_idx[length(seg_idx)]] else NA_real_

      rows[[row_id]] <- data.frame(
        group_id = group_id,
        segment_id = paste0(group_id, "_segment_", seg_i),
        segment_index = seg_i,
        start_row = min(seg_idx),
        end_row = max(seg_idx),
        start_time = time_start,
        end_time = time_end,
        n_samples = length(seg_idx),
        n_finite = length(finite_x),
        as.data.frame(as.list(feat)),
        status = status,
        stringsAsFactors = FALSE,
        check.names = FALSE
      )

      row_id <- row_id + 1L
    }
  }

  features <- do.call(rbind, rows)
  rownames(features) <- NULL

  attr(features, "svm_feature_settings") <- list(
    eda_col = eda_col,
    time_col = time_col,
    group_cols = group_cols,
    segment_seconds = segment_seconds,
    samples_per_segment = samples_per_segment,
    sampling_rate = sampling_rate
  )

  class(features) <- unique(c("gazepoint_artifact_svm_features", class(features)))
  features
}

#' Flag EDA artifacts with a user-supplied SVM-style model
#'
#' Applies a user-supplied model or prediction function to segment-level
#' artifact features. No pretrained model is bundled, so this function avoids
#' pretending to reproduce any proprietary or externally trained classifier.
#'
#' @param x Either raw EDA data or output from
#'   `prepare_gazepoint_artifact_svm_features()`.
#' @param model Optional model object or function. If `NULL`, features are
#'   returned with missing artifact predictions.
#' @param feature_cols Optional feature columns used by the model.
#' @param probability_threshold Threshold for artifact probability.
#' @param ... Passed to `prepare_gazepoint_artifact_svm_features()` when `x`
#'   is raw data.
#'
#' @return A data frame with artifact probabilities/classes where available.
#' @export
flag_gazepoint_artifacts_svm <- function(x,
                                         model = NULL,
                                         feature_cols = NULL,
                                         probability_threshold = 0.5,
                                         ...) {
  if (!is.data.frame(x)) {
    stop("`x` must be a data frame.", call. = FALSE)
  }

  if (inherits(x, "gazepoint_artifact_svm_features")) {
    features <- x
  } else {
    features <- prepare_gazepoint_artifact_svm_features(x, ...)
  }

  default_features <- c(
    "mean_signal", "sd_signal", "min_signal", "max_signal", "range_signal",
    "median_abs_diff", "max_abs_diff", "slope", "zero_crossing_diff",
    "detail_energy"
  )

  if (is.null(feature_cols)) {
    feature_cols <- intersect(default_features, names(features))
  }

  missing_features <- setdiff(feature_cols, names(features))
  if (length(missing_features) > 0) {
    stop("Missing `feature_cols`: ", paste(missing_features, collapse = ", "), call. = FALSE)
  }

  out <- features
  out$artifact_probability <- NA_real_
  out$artifact_svm <- NA
  out$artifact_svm_status <- "no_model_supplied"

  if (is.null(model)) {
    attr(out, "svm_artifact_overview") <- data.frame(
      segment_rows = nrow(out),
      model_supplied = FALSE,
      flagged_segments = NA_integer_,
      status = "svm_features_prepared_no_model_supplied",
      interpretation = paste(
        "SVM artifact features were prepared but no classifier was supplied.",
        "Use a validated user-supplied model to create artifact labels."
      ),
      stringsAsFactors = FALSE
    )

    class(out) <- unique(c("gazepoint_artifact_svm_flags", class(out)))
    return(out)
  }

  newdata <- out[feature_cols]
  pred <- gpbiometrics_svm_predict(model, newdata)

  if (is.numeric(pred)) {
    prob <- as.numeric(pred)
    out$artifact_probability <- prob
    out$artifact_svm <- prob >= probability_threshold
    out$artifact_svm_status <- "predicted_from_numeric_probability"
  } else {
    pred_chr <- as.character(pred)
    artifact_label <- tolower(pred_chr) %in% c("artifact", "art", "1", "true", "bad")
    out$artifact_svm <- artifact_label
    out$artifact_svm_status <- "predicted_from_class_label"
  }

  attr(out, "svm_artifact_overview") <- data.frame(
    segment_rows = nrow(out),
    model_supplied = TRUE,
    flagged_segments = sum(out$artifact_svm %in% TRUE, na.rm = TRUE),
    status = "svm_artifact_flags_created",
    interpretation = paste(
      "Artifact labels come from the supplied model.",
      "Validity depends on the model training data, features, scaling, and target device context."
    ),
    stringsAsFactors = FALSE
  )

  class(out) <- unique(c("gazepoint_artifact_svm_flags", class(out)))
  out
}

gpbiometrics_svm_split <- function(dat, group_cols) {
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

gpbiometrics_svm_sampling_rate <- function(time_values, sampling_rate = NULL) {
  if (!is.null(sampling_rate)) {
    return(sampling_rate)
  }

  time_values <- time_values[is.finite(time_values)]

  if (length(time_values) < 3) {
    return(NA_real_)
  }

  dt <- diff(time_values)
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

gpbiometrics_svm_detail_energy <- function(x) {
  if (length(x) < 2) {
    return(NA_real_)
  }

  if (length(x) %% 2 == 1) {
    x <- x[-length(x)]
  }

  detail <- (x[seq(1, length(x), by = 2)] - x[seq(2, length(x), by = 2)]) / sqrt(2)
  mean(detail^2, na.rm = TRUE)
}

gpbiometrics_svm_predict <- function(model, newdata) {
  if (is.function(model)) {
    return(model(newdata))
  }

  pred <- tryCatch(
    stats::predict(model, newdata = newdata, type = "response"),
    error = function(e) NULL
  )

  if (is.null(pred)) {
    pred <- tryCatch(
      stats::predict(model, newdata = newdata),
      error = function(e) {
        stop("Could not obtain predictions from `model`: ", conditionMessage(e), call. = FALSE)
      }
    )
  }

  pred
}
