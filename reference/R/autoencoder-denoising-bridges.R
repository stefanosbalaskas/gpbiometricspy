#' Denoise EDA using a user-supplied autoencoder reconstruction model
#'
#' Applies a user-supplied reconstruction function or model to fixed-length EDA
#' windows. No pretrained neural network is bundled. This function is an
#' interoperability bridge for validated user-supplied autoencoders.
#'
#' @param dat A data frame.
#' @param eda_col Numeric EDA column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param model A user-supplied function or model. If `NULL`, the original
#'   signal is copied and status records that no model was supplied.
#' @param window_samples Window length in samples.
#' @param output_col Optional output column.
#' @param overwrite Logical. If `FALSE`, existing output column is protected.
#'
#' @return A data frame with reconstructed signal and denoising attributes.
#' @export
denoise_gazepoint_eda_autoencoder <- function(dat,
                                              eda_col = "GSR_US",
                                              time_col = NULL,
                                              group_cols = NULL,
                                              model = NULL,
                                              window_samples = 128,
                                              output_col = NULL,
                                              overwrite = FALSE) {
  gpbiometrics_autoencoder_denoise_signal(
    dat = dat,
    signal_col = eda_col,
    signal_type = "EDA",
    time_col = time_col,
    group_cols = group_cols,
    model = model,
    window_samples = window_samples,
    output_col = output_col,
    overwrite = overwrite
  )
}

#' Denoise PPG using a user-supplied autoencoder reconstruction model
#'
#' Applies a user-supplied reconstruction function or model to fixed-length PPG
#' windows. No pretrained neural network is bundled. This function is an
#' interoperability bridge for validated user-supplied autoencoders.
#'
#' @param dat A data frame.
#' @param ppg_col Numeric PPG/pulse column.
#' @param time_col Optional time column.
#' @param group_cols Optional grouping columns.
#' @param model A user-supplied function or model. If `NULL`, the original
#'   signal is copied and status records that no model was supplied.
#' @param window_samples Window length in samples.
#' @param output_col Optional output column.
#' @param overwrite Logical. If `FALSE`, existing output column is protected.
#'
#' @return A data frame with reconstructed signal and denoising attributes.
#' @export
denoise_gazepoint_ppg_autoencoder <- function(dat,
                                              ppg_col = "HRP",
                                              time_col = NULL,
                                              group_cols = NULL,
                                              model = NULL,
                                              window_samples = 128,
                                              output_col = NULL,
                                              overwrite = FALSE) {
  gpbiometrics_autoencoder_denoise_signal(
    dat = dat,
    signal_col = ppg_col,
    signal_type = "PPG",
    time_col = time_col,
    group_cols = group_cols,
    model = model,
    window_samples = window_samples,
    output_col = output_col,
    overwrite = overwrite
  )
}

gpbiometrics_autoencoder_denoise_signal <- function(dat,
                                                    signal_col,
                                                    signal_type,
                                                    time_col = NULL,
                                                    group_cols = NULL,
                                                    model = NULL,
                                                    window_samples = 128,
                                                    output_col = NULL,
                                                    overwrite = FALSE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  if (!signal_col %in% names(dat)) {
    stop("Column `", signal_col, "` was not found in `dat`.", call. = FALSE)
  }

  if (!is.numeric(dat[[signal_col]])) {
    stop("`signal_col` must identify a numeric column.", call. = FALSE)
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

  if (is.null(output_col)) {
    output_col <- paste0(signal_col, "_autoencoder_denoised")
  }

  if (!isTRUE(overwrite) && output_col %in% names(dat)) {
    stop("Output column `", output_col, "` already exists. Use `overwrite = TRUE`.", call. = FALSE)
  }

  if (!is.numeric(window_samples) ||
      length(window_samples) != 1 ||
      !is.finite(window_samples) ||
      window_samples < 4) {
    stop("`window_samples` must be a positive number >= 4.", call. = FALSE)
  }

  window_samples <- as.integer(window_samples)

  out <- dat
  out[[output_col]] <- NA_real_

  status_col <- paste0(output_col, "_status")
  out[[status_col]] <- "not_processed"

  groups <- gpbiometrics_autoencoder_split(out, group_cols)

  summary_rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(out[[time_col]][idx])]
    }

    x <- out[[signal_col]][idx]
    finite <- is.finite(x)

    if (sum(finite) < 4) {
      out[[output_col]][idx] <<- NA_real_
      out[[status_col]][idx] <<- "insufficient_finite_samples"

      return(data.frame(
        group_id = group_id,
        n_rows = length(idx),
        n_finite = sum(finite),
        model_supplied = !is.null(model),
        status = "insufficient_finite_samples",
        stringsAsFactors = FALSE
      ))
    }

    x_filled <- gpbiometrics_autoencoder_fill(x)

    reconstructed <- if (is.null(model)) {
      x_filled
    } else {
      gpbiometrics_autoencoder_apply_model(
        model = model,
        x = x_filled,
        window_samples = window_samples
      )
    }

    reconstructed[!finite] <- NA_real_

    out[[output_col]][idx] <<- reconstructed
    out[[status_col]][idx] <<- if (is.null(model)) {
      "copied_no_autoencoder_model_supplied"
    } else {
      "autoencoder_reconstruction_applied"
    }

    data.frame(
      group_id = group_id,
      n_rows = length(idx),
      n_finite = sum(finite),
      model_supplied = !is.null(model),
      status = if (is.null(model)) {
        "copied_no_autoencoder_model_supplied"
      } else {
        "autoencoder_reconstruction_applied"
      },
      stringsAsFactors = FALSE
    )
  })

  summary_table <- do.call(rbind, summary_rows)
  rownames(summary_table) <- NULL

  overview <- data.frame(
    signal_type = signal_type,
    input_rows = nrow(dat),
    group_count = length(groups),
    model_supplied = !is.null(model),
    output_col = output_col,
    status = if (is.null(model)) {
      "autoencoder_bridge_no_model_supplied"
    } else {
      "autoencoder_reconstruction_complete"
    },
    interpretation = paste(
      "Autoencoder denoising requires a validated user-supplied reconstruction model.",
      "No pretrained neural network is bundled and outputs should be inspected against raw signals."
    ),
    stringsAsFactors = FALSE
  )

  attr(out, "autoencoder_denoising_overview") <- overview
  attr(out, "autoencoder_denoising_summary") <- summary_table
  attr(out, "autoencoder_denoising_settings") <- list(
    signal_col = signal_col,
    signal_type = signal_type,
    time_col = time_col,
    group_cols = group_cols,
    model_supplied = !is.null(model),
    window_samples = window_samples,
    output_col = output_col,
    overwrite = overwrite
  )

  class(out) <- unique(c("gazepoint_autoencoder_denoised", class(out)))
  out
}

gpbiometrics_autoencoder_split <- function(dat, group_cols) {
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

gpbiometrics_autoencoder_fill <- function(x) {
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

gpbiometrics_autoencoder_apply_model <- function(model,
                                                 x,
                                                 window_samples = 128) {
  starts <- seq(1, length(x), by = window_samples)
  recon <- numeric(length(x))

  for (start in starts) {
    end <- min(start + window_samples - 1, length(x))
    segment <- x[start:end]

    padded_length <- window_samples
    padded <- c(segment, rep(segment[length(segment)], padded_length - length(segment)))

    pred <- if (is.function(model)) {
      model(matrix(padded, nrow = 1))
    } else {
      tryCatch(
        stats::predict(model, newdata = matrix(padded, nrow = 1)),
        error = function(e) {
          stop("Could not obtain reconstruction from `model`: ", conditionMessage(e), call. = FALSE)
        }
      )
    }

    pred <- as.numeric(pred)

    if (length(pred) < length(segment)) {
      stop("Autoencoder reconstruction returned fewer values than the input segment.", call. = FALSE)
    }

    recon[start:end] <- pred[seq_along(segment)]
  }

  recon
}
