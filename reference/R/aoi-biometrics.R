#' Summarise biometric signals by AOI
#'
#' Summarises Gazepoint biometric channels within area-of-interest (AOI) rows.
#' The helper is intended for AOI-linked physiological descriptions, not for
#' inferring emotional valence.
#'
#' @param data A Gazepoint data frame containing AOI labels and biometric signals.
#' @param aoi_col AOI label column.
#' @param signal_cols Biometric signal columns to summarise.
#' @param group_cols Optional grouping columns, for example participant/media.
#' @param time_col Optional time/counter column.
#' @param valid_aoi_values Optional AOI labels to retain.
#' @param drop_missing_aoi Logical. If `TRUE`, rows with missing/blank AOI labels
#'   are excluded.
#' @param min_rows Minimum rows required for a group/AOI/signal summary to be
#'   marked as usable.
#'
#' @return A list with `overview`, `summary`, `signal_summary`, `aoi_summary`,
#'   `data`, and `settings`.
#' @export
summarise_gazepoint_aoi_biometrics <- function(data,
                                               aoi_col = "AOI",
                                               signal_cols = NULL,
                                               group_cols = NULL,
                                               time_col = NULL,
                                               valid_aoi_values = NULL,
                                               drop_missing_aoi = TRUE,
                                               min_rows = 1) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)

  if (!aoi_col %in% names(dat)) {
    stop("`aoi_col` was not found in `data`.", call. = FALSE)
  }

  if (is.null(signal_cols)) {
    signal_cols <- gpbiometrics_aoi_biometrics_default_signals(names(dat))
  }

  signal_cols <- unique(signal_cols)
  missing_signals <- setdiff(signal_cols, names(dat))

  if (length(missing_signals) > 0) {
    stop(
      "`signal_cols` were not found in `data`: ",
      paste(missing_signals, collapse = ", "),
      call. = FALSE
    )
  }

  if (length(signal_cols) == 0) {
    stop("No biometric signal columns were supplied or detected.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- gpbiometrics_aoi_biometrics_default_groups(names(dat))
  }

  missing_groups <- setdiff(group_cols, names(dat))

  if (length(missing_groups) > 0) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(missing_groups, collapse = ", "),
      call. = FALSE
    )
  }

  if (!is.null(time_col) && !time_col %in% names(dat)) {
    stop("`time_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.logical(drop_missing_aoi) ||
      length(drop_missing_aoi) != 1 ||
      is.na(drop_missing_aoi)) {
    stop("`drop_missing_aoi` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(min_rows) ||
      length(min_rows) != 1 ||
      !is.finite(min_rows) ||
      min_rows < 1) {
    stop("`min_rows` must be a single positive finite number.", call. = FALSE)
  }

  dat$.aoi_label <- as.character(dat[[aoi_col]])
  dat$.aoi_label[is.na(dat$.aoi_label)] <- NA_character_
  dat$.aoi_label[trimws(dat$.aoi_label) == ""] <- NA_character_

  if (isTRUE(drop_missing_aoi)) {
    dat <- dat[!is.na(dat$.aoi_label), , drop = FALSE]
  }

  if (!is.null(valid_aoi_values)) {
    dat <- dat[dat$.aoi_label %in% as.character(valid_aoi_values), , drop = FALSE]
  }

  if (nrow(dat) == 0) {
    empty_summary <- data.frame()

    overview <- data.frame(
      input_rows = nrow(data),
      retained_rows = 0L,
      aoi_count = 0L,
      signal_count = length(signal_cols),
      summary_rows = 0L,
      group_count = 0L,
      status = "fail_no_aoi_rows",
      stringsAsFactors = FALSE
    )

    return(structure(
      list(
        overview = overview,
        summary = empty_summary,
        signal_summary = empty_summary,
        aoi_summary = empty_summary,
        data = dat,
        settings = list(
          aoi_col = aoi_col,
          signal_cols = signal_cols,
          group_cols = group_cols,
          time_col = time_col,
          valid_aoi_values = valid_aoi_values,
          drop_missing_aoi = drop_missing_aoi,
          min_rows = min_rows
        )
      ),
      class = c("gazepoint_aoi_biometrics_summary", "list")
    ))
  }

  dat$.group_id <- gpbiometrics_aoi_biometrics_group_id(dat, group_cols)

  summary <- gpbiometrics_aoi_biometrics_make_summary(
    dat = dat,
    group_cols = group_cols,
    signal_cols = signal_cols,
    min_rows = min_rows
  )

  signal_summary <- gpbiometrics_aoi_biometrics_signal_summary(summary)
  aoi_summary <- gpbiometrics_aoi_biometrics_aoi_summary(summary)

  overview <- data.frame(
    input_rows = nrow(data),
    retained_rows = nrow(dat),
    aoi_count = length(unique(dat$.aoi_label)),
    signal_count = length(signal_cols),
    summary_rows = nrow(summary),
    group_count = length(unique(dat$.group_id)),
    usable_summary_rows = sum(summary$summary_status == "usable", na.rm = TRUE),
    low_row_summary_rows = sum(summary$summary_status == "warn_low_rows", na.rm = TRUE),
    status = if (nrow(summary) == 0) {
      "fail_no_aoi_biometric_summaries"
    } else if (any(summary$summary_status == "warn_low_rows", na.rm = TRUE)) {
      "warn_low_rows_in_some_summaries"
    } else {
      "aoi_biometrics_summarised"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      summary = summary,
      signal_summary = signal_summary,
      aoi_summary = aoi_summary,
      data = dat,
      settings = list(
        aoi_col = aoi_col,
        signal_cols = signal_cols,
        group_cols = group_cols,
        time_col = time_col,
        valid_aoi_values = valid_aoi_values,
        drop_missing_aoi = drop_missing_aoi,
        min_rows = min_rows,
        interpretation_notes = c(
          "AOI-linked biometrics summarise signals while AOI labels are active.",
          "EDA/GSR and HR summaries should not be interpreted as emotional valence.",
          "AOI dwell and biometric timing should be checked before confirmatory modelling."
        )
      )
    ),
    class = c("gazepoint_aoi_biometrics_summary", "list")
  )
}

#' Prepare AOI-biometric model data
#'
#' Converts AOI-biometric summaries into a modelling-ready table for GLM/LMM/GLMM
#' workflows.
#'
#' @param x A `gazepoint_aoi_biometrics_summary` object or summary data frame.
#' @param outcome_col Outcome column to model.
#' @param predictor_cols Optional predictor columns to retain.
#' @param factor_cols Optional columns converted to factors.
#' @param numeric_cols Optional columns converted to numeric.
#' @param group_cols Optional grouping columns for random-effect formulas.
#' @param drop_missing_outcome Logical. If `TRUE`, rows with missing outcomes are
#'   removed.
#' @param min_rows Optional minimum contributing rows required.
#' @param standardise_outcome Logical. If `TRUE`, add a z-scored outcome column.
#' @param standardise_within Standardization scope used when
#'   `standardise_outcome = TRUE`. Use `"signal"` to z-score within each
#'   biometric signal or `"all"` to z-score across all rows.
#'
#' @return A list with `overview`, `model_data`, `variable_summary`,
#'   `model_formulas`, and `settings`.
#' @export
prepare_gazepoint_aoi_biometrics_model_data <- function(x,
                                                        outcome_col = "mean_value",
                                                        predictor_cols = c("aoi_label", "signal"),
                                                        factor_cols = c("aoi_label", "signal"),
                                                        numeric_cols = NULL,
                                                        group_cols = NULL,
                                                        drop_missing_outcome = TRUE,
                                                        min_rows = NULL,
                                                        standardise_outcome = FALSE,
                                                        standardise_within = c("signal", "all")) {
  standardise_within <- match.arg(standardise_within)

  dat <- gpbiometrics_aoi_biometrics_extract_summary(x)

  if (!outcome_col %in% names(dat)) {
    stop("`outcome_col` was not found in the summary data.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- intersect(
      c(
        "source_participant",
        "participant",
        "subject",
        "source_file",
        "MEDIA_ID",
        "MEDIA_NAME"
      ),
      names(dat)
    )
  }

  keep_cols <- unique(c(
    predictor_cols,
    factor_cols,
    numeric_cols,
    group_cols,
    outcome_col,
    "n_rows",
    "n_finite",
    "summary_status"
  ))

  if (isTRUE(standardise_outcome) &&
      identical(standardise_within, "signal")) {
    if (!"signal" %in% names(dat)) {
      stop(
        "`standardise_within = \"signal\"` requires a `signal` column.",
        call. = FALSE
      )
    }

    keep_cols <- unique(c(keep_cols, "signal"))
  }

  keep_cols <- keep_cols[keep_cols %in% names(dat)]

  model_data <- dat[, keep_cols, drop = FALSE]

  if (!is.null(min_rows)) {
    if (!is.numeric(min_rows) ||
        length(min_rows) != 1 ||
        !is.finite(min_rows) ||
        min_rows < 1) {
      stop("`min_rows` must be NULL or a single positive finite number.", call. = FALSE)
    }

    if ("n_rows" %in% names(model_data)) {
      model_data <- model_data[model_data$n_rows >= min_rows, , drop = FALSE]
    }
  }

  if (isTRUE(drop_missing_outcome)) {
    outcome <- suppressWarnings(as.numeric(model_data[[outcome_col]]))
    model_data <- model_data[is.finite(outcome), , drop = FALSE]
  }

  for (col in factor_cols) {
    if (col %in% names(model_data)) {
      model_data[[col]] <- as.factor(model_data[[col]])
    }
  }

  for (col in numeric_cols) {
    if (col %in% names(model_data)) {
      model_data[[col]] <- suppressWarnings(as.numeric(model_data[[col]]))
    }
  }

  model_data[[outcome_col]] <- suppressWarnings(as.numeric(model_data[[outcome_col]]))

  z_col <- NA_character_

  if (isTRUE(standardise_outcome)) {
    z_col <- paste0(outcome_col, "_z")

    if (identical(standardise_within, "signal")) {
      model_data[[z_col]] <- NA_real_
      signal_key <- as.character(model_data$signal)
      signal_key[is.na(signal_key)] <- "<NA>"

      for (sig in unique(signal_key)) {
        idx <- which(signal_key == sig)
        model_data[[z_col]][idx] <-
          gpbiometrics_aoi_biometrics_standardise(
            model_data[[outcome_col]][idx]
          )
      }
    } else {
      model_data[[z_col]] <-
        gpbiometrics_aoi_biometrics_standardise(
          model_data[[outcome_col]]
        )
    }
  }

  variable_summary <- gpbiometrics_aoi_biometrics_variable_summary(
    model_data = model_data,
    outcome_col = outcome_col,
    predictor_cols = predictor_cols,
    factor_cols = factor_cols,
    group_cols = group_cols
  )

  fixed_terms <- predictor_cols[predictor_cols %in% names(model_data)]
  random_terms <- group_cols[group_cols %in% names(model_data)]

  fixed_part <- if (length(fixed_terms) > 0) {
    paste(fixed_terms, collapse = " + ")
  } else {
    "1"
  }

  random_part <- if (length(random_terms) > 0) {
    paste(paste0("(1 | ", random_terms, ")"), collapse = " + ")
  } else {
    NULL
  }

  rhs <- paste(c(fixed_part, random_part), collapse = " + ")

  model_formulas <- data.frame(
    outcome = outcome_col,
    formula = paste(outcome_col, "~", rhs),
    z_outcome = if (isTRUE(standardise_outcome)) z_col else NA_character_,
    z_formula = if (isTRUE(standardise_outcome)) paste(z_col, "~", rhs) else NA_character_,
    stringsAsFactors = FALSE
  )

  overview <- data.frame(
    input_rows = nrow(dat),
    model_rows = nrow(model_data),
    outcome_col = outcome_col,
    predictor_count = length(fixed_terms),
    factor_count = sum(factor_cols %in% names(model_data)),
    group_count = length(random_terms),
    standardise_outcome = isTRUE(standardise_outcome),
    standardise_within = if (isTRUE(standardise_outcome)) {
      standardise_within
    } else {
      NA_character_
    },
    status = if (nrow(model_data) == 0) {
      "fail_no_model_rows"
    } else {
      "aoi_biometrics_model_data_prepared"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      model_data = model_data,
      variable_summary = variable_summary,
      model_formulas = model_formulas,
      settings = list(
        outcome_col = outcome_col,
        predictor_cols = predictor_cols,
        factor_cols = factor_cols,
        numeric_cols = numeric_cols,
        group_cols = group_cols,
        drop_missing_outcome = drop_missing_outcome,
        min_rows = min_rows,
        standardise_outcome = standardise_outcome,
        standardise_within = standardise_within,
        interpretation_notes = c(
          "Prepared data are intended for user-selected GLM/LMM/GLMM workflows.",
          "Model formulas are suggestions and should be adapted to study design.",
          "When multiple biometric signals are modelled together, within-signal standardization is usually safer than global standardization.",
          "Biometric outcomes should be interpreted as physiological signal summaries, not emotional valence."
        )
      )
    ),
    class = c("gazepoint_aoi_biometrics_model_data", "list")
  )
}

#' Plot AOI-linked biometric summaries
#'
#' Plots AOI-biometric summary values as a ggplot object.
#'
#' @param x A `gazepoint_aoi_biometrics_summary`,
#'   `gazepoint_aoi_biometrics_model_data`, or data frame.
#' @param value_col Value column to plot.
#' @param aoi_col AOI label column.
#' @param signal_col Signal label column.
#' @param group_col Optional grouping column.
#' @param plot_type `"boxplot"`, `"point"`, or `"line"`.
#' @param title Optional plot title.
#'
#' @return A ggplot object with plot data stored in attributes.
#' @export
plot_gazepoint_aoi_biometrics <- function(x,
                                          value_col = "mean_value",
                                          aoi_col = "aoi_label",
                                          signal_col = "signal",
                                          group_col = NULL,
                                          plot_type = c("boxplot", "point", "line"),
                                          title = NULL) {
  plot_type <- match.arg(plot_type)

  gpbiometrics_require_ggplot2()

  dat <- gpbiometrics_aoi_biometrics_extract_plot_data(x)

  required <- c(value_col, aoi_col, signal_col)
  missing_required <- setdiff(required, names(dat))

  if (length(missing_required) > 0) {
    stop(
      "Required plotting columns were not found: ",
      paste(missing_required, collapse = ", "),
      call. = FALSE
    )
  }

  dat$.plot_value <- suppressWarnings(as.numeric(dat[[value_col]]))
  dat$.plot_aoi <- as.factor(dat[[aoi_col]])
  dat$.plot_signal <- as.factor(dat[[signal_col]])

  if (!is.null(group_col)) {
    if (!group_col %in% names(dat)) {
      stop("`group_col` was not found in the plotting data.", call. = FALSE)
    }

    dat$.plot_group <- as.factor(dat[[group_col]])
  } else {
    dat$.plot_group <- factor("all")
  }

  dat <- dat[is.finite(dat$.plot_value), , drop = FALSE]

  p <- ggplot2::ggplot(
    dat,
    ggplot2::aes(
      x = .plot_aoi,
      y = .plot_value
    )
  ) +
    ggplot2::labs(
      title = if (is.null(title)) "AOI-linked biometric summaries" else title,
      x = aoi_col,
      y = value_col
    ) +
    ggplot2::theme_minimal()

  if (identical(plot_type, "boxplot")) {
    p <- p + ggplot2::geom_boxplot(na.rm = TRUE)
  } else if (identical(plot_type, "point")) {
    p <- p + ggplot2::geom_point(
      ggplot2::aes(group = .plot_group),
      position = ggplot2::position_jitter(width = 0.08, height = 0),
      na.rm = TRUE
    )
  } else {
    p <- p + ggplot2::geom_line(
      ggplot2::aes(group = .plot_group),
      na.rm = TRUE
    ) +
      ggplot2::geom_point(na.rm = TRUE)
  }

  if (length(unique(dat$.plot_signal)) > 1) {
    p <- p + ggplot2::facet_wrap(
      stats::as.formula("~ .plot_signal"),
      scales = "free_y"
    )
  }

  settings <- list(
    value_col = value_col,
    aoi_col = aoi_col,
    signal_col = signal_col,
    group_col = group_col,
    plot_type = plot_type,
    interpretation_notes = c(
      "The plot displays biometric summaries by AOI.",
      "Biometric differences by AOI should not be interpreted as emotional valence without additional evidence."
    )
  )

  standardise_gazepoint_plot_contract(
    plot = p,
    plot_data = dat,
    settings = settings,
    interpretation_notes = settings$interpretation_notes,
    plot_type = plot_type
  )
}

gpbiometrics_aoi_biometrics_default_signals <- function(names_dat) {
  candidates <- c(
    "GSR_US",
    "GSR_US_TONIC",
    "GSR_US_PHASIC",
    "GSR",
    "HR",
    "HRP",
    "IBI",
    "IBI_clean_ms",
    "DIAL"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_aoi_biometrics_default_groups <- function(names_dat) {
  candidates <- c(
    "source_file",
    "source_participant",
    "participant",
    "subject",
    "MEDIA_ID",
    "MEDIA_NAME",
    "trial",
    "trial_id",
    "trial_global"
  )

  unique(candidates[candidates %in% names_dat])
}

gpbiometrics_aoi_biometrics_group_id <- function(dat, group_cols) {
  if (length(group_cols) == 0) {
    return(rep("all", nrow(dat)))
  }

  group_dat <- dat[group_cols]

  group_dat[] <- lapply(group_dat, function(x) {
    x_chr <- as.character(x)
    x_chr[is.na(x_chr)] <- "<NA>"
    x_chr
  })

  apply(group_dat, 1, paste, collapse = "||")
}

gpbiometrics_aoi_biometrics_make_summary <- function(dat,
                                                     group_cols,
                                                     signal_cols,
                                                     min_rows) {
  split_keys <- c(".group_id", ".aoi_label")
  groups <- split(dat, interaction(dat[split_keys], drop = TRUE), drop = TRUE)

  out <- list()

  counter <- 1L

  for (group_name in names(groups)) {
    d <- groups[[group_name]]

    for (signal in signal_cols) {
      value <- suppressWarnings(as.numeric(d[[signal]]))
      finite_value <- value[is.finite(value)]

      row <- data.frame(
        aoi_label = d$.aoi_label[1],
        group_id = d$.group_id[1],
        signal = signal,
        n_rows = nrow(d),
        n_finite = length(finite_value),
        missing_rows = sum(!is.finite(value)),
        missing_prop = mean(!is.finite(value)),
        mean_value = if (length(finite_value) > 0) mean(finite_value, na.rm = TRUE) else NA_real_,
        median_value = if (length(finite_value) > 0) stats::median(finite_value, na.rm = TRUE) else NA_real_,
        sd_value = if (length(finite_value) > 1) stats::sd(finite_value, na.rm = TRUE) else NA_real_,
        min_value = if (length(finite_value) > 0) min(finite_value, na.rm = TRUE) else NA_real_,
        max_value = if (length(finite_value) > 0) max(finite_value, na.rm = TRUE) else NA_real_,
        first_value = if (length(finite_value) > 0) finite_value[1] else NA_real_,
        last_value = if (length(finite_value) > 0) finite_value[length(finite_value)] else NA_real_,
        delta_value = if (length(finite_value) > 1) {
          finite_value[length(finite_value)] - finite_value[1]
        } else {
          NA_real_
        },
        auc_value = if (length(finite_value) > 0) sum(finite_value, na.rm = TRUE) else NA_real_,
        summary_status = if (nrow(d) < min_rows || length(finite_value) < min_rows) {
          "warn_low_rows"
        } else {
          "usable"
        },
        stringsAsFactors = FALSE
      )

      if (length(group_cols) > 0 && all(group_cols %in% names(d))) {
        row <- cbind(d[1, group_cols, drop = FALSE], row)
      }

      out[[counter]] <- row
      counter <- counter + 1L
    }
  }

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_aoi_biometrics_signal_summary <- function(summary) {
  if (nrow(summary) == 0) {
    return(data.frame())
  }

  signals <- unique(summary$signal)

  out <- lapply(signals, function(signal) {
    d <- summary[summary$signal == signal, , drop = FALSE]
    data.frame(
      signal = signal,
      summary_rows = nrow(d),
      usable_rows = sum(d$summary_status == "usable", na.rm = TRUE),
      aoi_count = length(unique(d$aoi_label)),
      mean_of_means = mean(d$mean_value, na.rm = TRUE),
      median_of_means = stats::median(d$mean_value, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_aoi_biometrics_aoi_summary <- function(summary) {
  if (nrow(summary) == 0) {
    return(data.frame())
  }

  aois <- unique(summary$aoi_label)

  out <- lapply(aois, function(aoi) {
    d <- summary[summary$aoi_label == aoi, , drop = FALSE]
    data.frame(
      aoi_label = aoi,
      summary_rows = nrow(d),
      usable_rows = sum(d$summary_status == "usable", na.rm = TRUE),
      signal_count = length(unique(d$signal)),
      total_rows_contributing = sum(d$n_rows, na.rm = TRUE),
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_aoi_biometrics_extract_summary <- function(x) {
  if (inherits(x, "gazepoint_aoi_biometrics_summary") &&
      !is.null(x$summary)) {
    return(as.data.frame(x$summary, stringsAsFactors = FALSE))
  }

  if (is.data.frame(x)) {
    return(as.data.frame(x, stringsAsFactors = FALSE))
  }

  stop("`x` must be an AOI-biometric summary object or a data frame.", call. = FALSE)
}

gpbiometrics_aoi_biometrics_extract_plot_data <- function(x) {
  if (inherits(x, "gazepoint_aoi_biometrics_summary") &&
      !is.null(x$summary)) {
    return(as.data.frame(x$summary, stringsAsFactors = FALSE))
  }

  if (inherits(x, "gazepoint_aoi_biometrics_model_data") &&
      !is.null(x$model_data)) {
    return(as.data.frame(x$model_data, stringsAsFactors = FALSE))
  }

  if (is.data.frame(x)) {
    return(as.data.frame(x, stringsAsFactors = FALSE))
  }

  stop("`x` must be an AOI-biometric object or a data frame.", call. = FALSE)
}

gpbiometrics_aoi_biometrics_variable_summary <- function(model_data,
                                                         outcome_col,
                                                         predictor_cols,
                                                         factor_cols,
                                                         group_cols) {
  if (nrow(model_data) == 0) {
    return(data.frame())
  }

  cols <- unique(c(outcome_col, predictor_cols, factor_cols, group_cols))
  cols <- cols[cols %in% names(model_data)]

  out <- lapply(cols, function(col) {
    x <- model_data[[col]]
    is_num <- is.numeric(x)

    data.frame(
      variable = col,
      class = paste(class(x), collapse = "/"),
      n = length(x),
      missing = sum(is.na(x)),
      unique_values = length(unique(x[!is.na(x)])),
      mean = if (is_num) mean(x, na.rm = TRUE) else NA_real_,
      sd = if (is_num) stats::sd(x, na.rm = TRUE) else NA_real_,
      stringsAsFactors = FALSE
    )
  })

  out <- do.call(rbind, out)
  rownames(out) <- NULL

  out
}

gpbiometrics_aoi_biometrics_standardise <- function(x) {
  x <- suppressWarnings(as.numeric(x))
  x_mean <- mean(x, na.rm = TRUE)
  x_sd <- stats::sd(x, na.rm = TRUE)

  if (is.finite(x_sd) && x_sd > 0) {
    (x - x_mean) / x_sd
  } else {
    ifelse(is.na(x), NA_real_, 0)
  }
}
