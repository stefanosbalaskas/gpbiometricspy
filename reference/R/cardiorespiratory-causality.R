#' Analyse cardiorespiratory Granger-style directionality
#'
#' Computes dependency-light linear Granger-style directionality tests between a
#' respiration proxy and heart-rate or IBI/RR signal. This estimates predictive
#' directionality in a VAR-style model. It does not prove physiological
#' causality from observational data by itself.
#'
#' @param dat A data frame.
#' @param respiration_col Numeric respiration proxy column.
#' @param cardiac_col Numeric cardiac column, such as HR, IBI, or RR.
#' @param time_col Optional time column for ordering.
#' @param group_cols Optional grouping columns.
#' @param lag_order VAR lag order.
#' @param min_rows Minimum complete rows per group.
#' @param standardise Logical. If `TRUE`, z-standardise both series per group.
#'
#' @return A list with `overview`, `causality_summary`, and `settings`.
#' @export
analyze_gazepoint_cardiorespiratory_causality <- function(dat,
                                                          respiration_col,
                                                          cardiac_col,
                                                          time_col = NULL,
                                                          group_cols = NULL,
                                                          lag_order = 3,
                                                          min_rows = 30,
                                                          standardise = TRUE) {
  if (!is.data.frame(dat)) {
    stop("`dat` must be a data frame.", call. = FALSE)
  }

  required <- c(respiration_col, cardiac_col, time_col)
  required <- required[!is.null(required)]

  missing_required <- setdiff(required, names(dat))
  if (length(missing_required) > 0) {
    stop("Missing required columns: ", paste(missing_required, collapse = ", "), call. = FALSE)
  }

  if (!is.numeric(dat[[respiration_col]])) {
    stop("`respiration_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.numeric(dat[[cardiac_col]])) {
    stop("`cardiac_col` must identify a numeric column.", call. = FALSE)
  }

  if (!is.null(time_col) && !is.numeric(dat[[time_col]])) {
    stop("`time_col` must identify a numeric column.", call. = FALSE)
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  }

  missing_groups <- setdiff(group_cols, names(dat))
  if (length(missing_groups) > 0) {
    stop("Missing `group_cols`: ", paste(missing_groups, collapse = ", "), call. = FALSE)
  }

  groups <- gpbiometrics_cardioresp_split(dat, group_cols)

  rows <- lapply(names(groups), function(group_id) {
    idx <- groups[[group_id]]

    if (!is.null(time_col)) {
      idx <- idx[order(dat[[time_col]][idx])]
    }

    resp <- dat[[respiration_col]][idx]
    cardiac <- dat[[cardiac_col]][idx]

    keep <- is.finite(resp) & is.finite(cardiac)
    resp <- resp[keep]
    cardiac <- cardiac[keep]

    if (length(resp) < min_rows ||
        length(resp) <= lag_order * 3 ||
        stats::sd(resp) == 0 ||
        stats::sd(cardiac) == 0) {
      return(data.frame(
        group_id = group_id,
        n_rows = length(resp),
        lag_order = lag_order,
        respiration_to_cardiac_f = NA_real_,
        respiration_to_cardiac_p = NA_real_,
        respiration_to_cardiac_log_ratio = NA_real_,
        cardiac_to_respiration_f = NA_real_,
        cardiac_to_respiration_p = NA_real_,
        cardiac_to_respiration_log_ratio = NA_real_,
        dominant_direction = NA_character_,
        status = "insufficient_information",
        stringsAsFactors = FALSE
      ))
    }

    if (isTRUE(standardise)) {
      resp <- as.numeric(scale(resp))
      cardiac <- as.numeric(scale(cardiac))
    }

    r_to_c <- gpbiometrics_granger_test(
      target = cardiac,
      driver = resp,
      lag_order = lag_order
    )

    c_to_r <- gpbiometrics_granger_test(
      target = resp,
      driver = cardiac,
      lag_order = lag_order
    )

    dominant <- if (is.finite(r_to_c$log_ratio) && is.finite(c_to_r$log_ratio)) {
      if (r_to_c$log_ratio > c_to_r$log_ratio) {
        "respiration_to_cardiac_stronger"
      } else if (c_to_r$log_ratio > r_to_c$log_ratio) {
        "cardiac_to_respiration_stronger"
      } else {
        "balanced"
      }
    } else {
      NA_character_
    }

    data.frame(
      group_id = group_id,
      n_rows = length(resp),
      lag_order = lag_order,
      respiration_to_cardiac_f = r_to_c$f_value,
      respiration_to_cardiac_p = r_to_c$p_value,
      respiration_to_cardiac_log_ratio = r_to_c$log_ratio,
      cardiac_to_respiration_f = c_to_r$f_value,
      cardiac_to_respiration_p = c_to_r$p_value,
      cardiac_to_respiration_log_ratio = c_to_r$log_ratio,
      dominant_direction = dominant,
      status = "granger_directionality_estimated",
      stringsAsFactors = FALSE
    )
  })

  causality_summary <- do.call(rbind, rows)
  rownames(causality_summary) <- NULL

  overview <- data.frame(
    group_count = length(groups),
    result_rows = nrow(causality_summary),
    successful_groups = sum(causality_summary$status == "granger_directionality_estimated"),
    problem_groups = sum(causality_summary$status != "granger_directionality_estimated"),
    status = if (all(causality_summary$status == "granger_directionality_estimated")) {
      "cardiorespiratory_directionality_estimated"
    } else if (any(causality_summary$status == "granger_directionality_estimated")) {
      "cardiorespiratory_directionality_partial"
    } else {
      "cardiorespiratory_directionality_failed"
    },
    interpretation = paste(
      "These are linear Granger-style predictive-directionality summaries.",
      "They do not prove mechanistic causality and should be interpreted with experimental design, stationarity, lag choice, and measurement quality."
    ),
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      causality_summary = causality_summary,
      settings = list(
        respiration_col = respiration_col,
        cardiac_col = cardiac_col,
        time_col = time_col,
        group_cols = group_cols,
        lag_order = lag_order,
        min_rows = min_rows,
        standardise = standardise
      )
    ),
    class = c("gazepoint_cardiorespiratory_causality", "list")
  )
}

gpbiometrics_cardioresp_split <- function(dat, group_cols) {
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

gpbiometrics_granger_test <- function(target, driver, lag_order = 3) {
  n <- length(target)

  response <- target[(lag_order + 1):n]

  target_lags <- sapply(seq_len(lag_order), function(lag) {
    target[(lag_order + 1 - lag):(n - lag)]
  })

  driver_lags <- sapply(seq_len(lag_order), function(lag) {
    driver[(lag_order + 1 - lag):(n - lag)]
  })

  target_lags <- as.data.frame(target_lags)
  driver_lags <- as.data.frame(driver_lags)

  names(target_lags) <- paste0("target_lag_", seq_len(lag_order))
  names(driver_lags) <- paste0("driver_lag_", seq_len(lag_order))

  reduced_dat <- data.frame(response = response, target_lags)
  full_dat <- data.frame(response = response, target_lags, driver_lags)

  reduced <- stats::lm(response ~ ., data = reduced_dat)
  full <- stats::lm(response ~ ., data = full_dat)

  rss_reduced <- sum(stats::residuals(reduced)^2)
  rss_full <- sum(stats::residuals(full)^2)

  df1 <- lag_order
  df2 <- stats::df.residual(full)

  f_value <- if (rss_full > 0 && df2 > 0) {
    ((rss_reduced - rss_full) / df1) / (rss_full / df2)
  } else {
    NA_real_
  }

  p_value <- if (is.finite(f_value)) {
    stats::pf(f_value, df1 = df1, df2 = df2, lower.tail = FALSE)
  } else {
    NA_real_
  }

  log_ratio <- if (is.finite(rss_reduced) && is.finite(rss_full) && rss_full > 0) {
    log(rss_reduced / rss_full)
  } else {
    NA_real_
  }

  list(
    f_value = f_value,
    p_value = p_value,
    log_ratio = log_ratio
  )
}
