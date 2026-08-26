#' Prepare Gazepoint biometric summaries for mixed-model analysis
#'
#' Prepares biometric window-level or event-level summaries for downstream
#' mixed-model analysis. This helper does not fit a model. It checks variables,
#' optionally baseline-corrects the selected outcome, optionally scales numeric
#' predictors, converts grouping/factor variables, flags complete cases, and
#' returns a conservative model formula.
#'
#' @param data A data frame containing biometric summary rows.
#' @param outcome_col Name of the outcome column to analyse.
#' @param fixed_effect_cols Optional fixed-effect predictor columns.
#' @param condition_cols Optional condition/design columns to include as fixed
#'   effects.
#' @param covariate_cols Optional covariate columns to include as fixed effects.
#' @param random_effect_cols Optional grouping columns for random intercepts.
#' @param participant_col,stimulus_col,trial_col Optional common grouping columns.
#' @param window_col Optional analysis-window column. Included as a fixed effect
#'   when `include_window = TRUE`.
#' @param baseline_col Optional baseline column.
#' @param baseline_correct Logical. If `TRUE`, creates an outcome column equal to
#'   `outcome_col - baseline_col`.
#' @param factor_cols Optional columns to convert to factors.
#' @param continuous_cols Optional numeric predictor columns to scale when
#'   `scale_continuous = TRUE`.
#' @param scale_continuous Logical. If `TRUE`, creates z-scored versions of
#'   numeric continuous predictors and uses those in the formula.
#' @param include_window Logical. Should `window_col` be included as a fixed
#'   effect?
#' @param drop_missing Logical. Should incomplete model rows be removed from
#'   `model_data`?
#' @param min_rows Minimum number of complete rows required for a `"ready"`
#'   status.
#'
#' @return A list with `overview`, `data`, `model_data`, `model_formula`,
#'   `variable_summary`, and `settings`.
#' @export
prepare_gazepoint_biometrics_lme_data <- function(data,
                                                  outcome_col,
                                                  fixed_effect_cols = NULL,
                                                  condition_cols = NULL,
                                                  covariate_cols = NULL,
                                                  random_effect_cols = NULL,
                                                  participant_col = NULL,
                                                  stimulus_col = NULL,
                                                  trial_col = NULL,
                                                  window_col = NULL,
                                                  baseline_col = NULL,
                                                  baseline_correct = FALSE,
                                                  factor_cols = NULL,
                                                  continuous_cols = NULL,
                                                  scale_continuous = FALSE,
                                                  include_window = TRUE,
                                                  drop_missing = TRUE,
                                                  min_rows = 10) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (missing(outcome_col) || length(outcome_col) != 1 || !is.character(outcome_col)) {
    stop("`outcome_col` must be a single column name.", call. = FALSE)
  }

  if (!outcome_col %in% names(data)) {
    stop("`outcome_col` was not found in `data`.", call. = FALSE)
  }

  if (!is.logical(baseline_correct) || length(baseline_correct) != 1) {
    stop("`baseline_correct` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(scale_continuous) || length(scale_continuous) != 1) {
    stop("`scale_continuous` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(include_window) || length(include_window) != 1) {
    stop("`include_window` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(drop_missing) || length(drop_missing) != 1) {
    stop("`drop_missing` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.numeric(min_rows) || length(min_rows) != 1 || min_rows < 1) {
    stop("`min_rows` must be a positive number.", call. = FALSE)
  }

  dat <- as.data.frame(data, stringsAsFactors = FALSE)
  dat$.gpbiometrics_original_row_id <- seq_len(nrow(dat))

  all_requested <- unique(stats::na.omit(c(
    fixed_effect_cols,
    condition_cols,
    covariate_cols,
    random_effect_cols,
    participant_col,
    stimulus_col,
    trial_col,
    window_col,
    baseline_col,
    factor_cols,
    continuous_cols
  )))

  missing_requested <- setdiff(all_requested, names(dat))

  if (length(missing_requested) > 0) {
    stop(
      "The following requested columns were not found in `data`: ",
      paste(missing_requested, collapse = ", "),
      call. = FALSE
    )
  }

  outcome_numeric <- suppressWarnings(as.numeric(dat[[outcome_col]]))

  if (all(is.na(outcome_numeric))) {
    stop("`outcome_col` must contain numeric values.", call. = FALSE)
  }

  dat[[outcome_col]] <- outcome_numeric
  analysis_outcome_col <- outcome_col

  if (isTRUE(baseline_correct)) {
    if (is.null(baseline_col)) {
      stop("`baseline_col` must be supplied when `baseline_correct = TRUE`.", call. = FALSE)
    }

    baseline_numeric <- suppressWarnings(as.numeric(dat[[baseline_col]]))

    if (all(is.na(baseline_numeric))) {
      stop("`baseline_col` must contain numeric values.", call. = FALSE)
    }

    dat[[baseline_col]] <- baseline_numeric

    analysis_outcome_col <- paste0(outcome_col, "_baseline_corrected")
    dat[[analysis_outcome_col]] <- dat[[outcome_col]] - dat[[baseline_col]]
  }

  inferred_random <- gpbiometrics_lme_infer_random_cols(
    names_dat = names(dat),
    random_effect_cols = random_effect_cols,
    participant_col = participant_col,
    stimulus_col = stimulus_col,
    trial_col = trial_col
  )

  random_effect_cols <- inferred_random

  fixed_terms <- unique(stats::na.omit(c(
    fixed_effect_cols,
    condition_cols,
    covariate_cols,
    if (isTRUE(include_window)) window_col else NULL
  )))

  factor_cols <- unique(stats::na.omit(c(
    factor_cols,
    fixed_terms[!vapply(dat[fixed_terms], is.numeric, logical(1))],
    random_effect_cols
  )))

  for (col in factor_cols) {
    dat[[col]] <- as.factor(dat[[col]])
  }

  if (is.null(continuous_cols)) {
    continuous_cols <- fixed_terms[
      vapply(dat[fixed_terms], is.numeric, logical(1))
    ]
  }

  continuous_cols <- unique(stats::na.omit(continuous_cols))

  scaled_map <- data.frame(
    original_col = character(),
    scaled_col = character(),
    stringsAsFactors = FALSE
  )

  formula_fixed_terms <- fixed_terms

  if (isTRUE(scale_continuous) && length(continuous_cols) > 0) {
    for (col in continuous_cols) {
      x <- suppressWarnings(as.numeric(dat[[col]]))
      x_mean <- mean(x, na.rm = TRUE)
      x_sd <- stats::sd(x, na.rm = TRUE)

      scaled_col <- paste0("z_", make.names(col))

      if (!is.finite(x_sd) || x_sd == 0) {
        dat[[scaled_col]] <- NA_real_
      } else {
        dat[[scaled_col]] <- (x - x_mean) / x_sd
      }

      formula_fixed_terms[formula_fixed_terms == col] <- scaled_col

      scaled_map <- rbind(
        scaled_map,
        data.frame(
          original_col = col,
          scaled_col = scaled_col,
          stringsAsFactors = FALSE
        )
      )
    }
  }

  required_model_cols <- unique(stats::na.omit(c(
    analysis_outcome_col,
    formula_fixed_terms,
    random_effect_cols
  )))

  complete_case <- stats::complete.cases(dat[, required_model_cols, drop = FALSE])
  dat$lme_complete_case <- complete_case

  model_data <- dat

  if (isTRUE(drop_missing)) {
    model_data <- model_data[model_data$lme_complete_case, , drop = FALSE]
  }

  formula_rhs <- "1"

  if (length(formula_fixed_terms) > 0) {
    formula_rhs <- paste(
      vapply(formula_fixed_terms, gpbiometrics_lme_formula_name, character(1)),
      collapse = " + "
    )
  }

  if (length(random_effect_cols) > 0) {
    random_rhs <- paste0(
      "(1 | ",
      vapply(random_effect_cols, gpbiometrics_lme_formula_name, character(1)),
      ")"
    )

    formula_rhs <- paste(c(formula_rhs, random_rhs), collapse = " + ")
  }

  formula_text <- paste(
    gpbiometrics_lme_formula_name(analysis_outcome_col),
    "~",
    formula_rhs
  )

  model_formula <- stats::as.formula(formula_text)

  n_complete <- sum(complete_case)

  status <- if (nrow(dat) == 0) {
    "empty_input"
  } else if (n_complete == 0) {
    "no_complete_model_rows"
  } else if (n_complete < min_rows) {
    "limited_complete_rows"
  } else {
    "ready"
  }

  variable_summary <- gpbiometrics_lme_variable_summary(
    dat = dat,
    variables = unique(stats::na.omit(c(
      analysis_outcome_col,
      outcome_col,
      baseline_col,
      formula_fixed_terms,
      fixed_terms,
      random_effect_cols
    ))),
    analysis_outcome_col = analysis_outcome_col,
    fixed_terms = formula_fixed_terms,
    random_effect_cols = random_effect_cols,
    baseline_col = baseline_col
  )

  structure(
    list(
      overview = data.frame(
        input_rows = nrow(dat),
        complete_model_rows = n_complete,
        model_rows = nrow(model_data),
        outcome_col = outcome_col,
        analysis_outcome_col = analysis_outcome_col,
        fixed_effect_count = length(formula_fixed_terms),
        random_effect_count = length(random_effect_cols),
        status = status,
        stringsAsFactors = FALSE
      ),
      data = dat,
      model_data = model_data,
      model_formula = model_formula,
      variable_summary = variable_summary,
      settings = list(
        outcome_col = outcome_col,
        analysis_outcome_col = analysis_outcome_col,
        fixed_effect_cols = fixed_effect_cols,
        condition_cols = condition_cols,
        covariate_cols = covariate_cols,
        formula_fixed_terms = formula_fixed_terms,
        random_effect_cols = random_effect_cols,
        participant_col = participant_col,
        stimulus_col = stimulus_col,
        trial_col = trial_col,
        window_col = window_col,
        baseline_col = baseline_col,
        baseline_correct = baseline_correct,
        factor_cols = factor_cols,
        continuous_cols = continuous_cols,
        scaled_map = scaled_map,
        scale_continuous = scale_continuous,
        include_window = include_window,
        drop_missing = drop_missing,
        min_rows = min_rows,
        formula_text = formula_text
      )
    ),
    class = c("gazepoint_biometrics_lme_data", "list")
  )
}

gpbiometrics_lme_first_existing <- function(names_dat, candidates) {
  exact <- candidates[candidates %in% names_dat]

  if (length(exact) > 0) {
    return(exact[1])
  }

  lower_names <- tolower(names_dat)
  lower_candidates <- tolower(candidates)
  idx <- match(lower_candidates, lower_names)
  idx <- idx[!is.na(idx)]

  if (length(idx) > 0) {
    return(names_dat[idx[1]])
  }

  NULL
}

gpbiometrics_lme_infer_random_cols <- function(names_dat,
                                               random_effect_cols,
                                               participant_col,
                                               stimulus_col,
                                               trial_col) {
  explicit <- unique(stats::na.omit(c(
    random_effect_cols,
    participant_col,
    stimulus_col,
    trial_col
  )))

  if (length(explicit) > 0) {
    return(explicit)
  }

  participant <- gpbiometrics_lme_first_existing(
    names_dat,
    c("participant", "subject", "subject_id", "USER", "USER_FILE", "user_file")
  )

  stimulus <- gpbiometrics_lme_first_existing(
    names_dat,
    c("stimulus", "stimulus_id", "MEDIA_ID", "MEDIA_NAME", "media_id", "media_name")
  )

  trial <- gpbiometrics_lme_first_existing(
    names_dat,
    c("trial", "trial_id", "TRIAL", "trial_global")
  )

  unique(stats::na.omit(c(participant, stimulus, trial)))
}

gpbiometrics_lme_formula_name <- function(x) {
  syntactic <- make.names(x) == x
  reserved <- x %in% c(
    "if", "else", "repeat", "while", "function", "for",
    "in", "next", "break", "TRUE", "FALSE", "NULL",
    "Inf", "NaN", "NA", "NA_integer_", "NA_real_",
    "NA_complex_", "NA_character_"
  )

  if (isTRUE(syntactic) && !reserved) {
    return(x)
  }

  paste0("`", gsub("`", "\\\\`", x), "`")
}

gpbiometrics_lme_variable_summary <- function(dat,
                                              variables,
                                              analysis_outcome_col,
                                              fixed_terms,
                                              random_effect_cols,
                                              baseline_col) {
  out <- data.frame(
    variable = variables,
    role = "other",
    class = NA_character_,
    missing_count = NA_integer_,
    unique_count = NA_integer_,
    stringsAsFactors = FALSE
  )

  for (i in seq_len(nrow(out))) {
    variable <- out$variable[i]

    out$class[i] <- paste(class(dat[[variable]]), collapse = ";")
    out$missing_count[i] <- sum(is.na(dat[[variable]]))
    out$unique_count[i] <- length(unique(dat[[variable]][!is.na(dat[[variable]])]))

    if (variable == analysis_outcome_col) {
      out$role[i] <- "analysis_outcome"
    } else if (variable %in% fixed_terms) {
      out$role[i] <- "fixed_effect"
    } else if (variable %in% random_effect_cols) {
      out$role[i] <- "random_effect"
    } else if (!is.null(baseline_col) && variable == baseline_col) {
      out$role[i] <- "baseline"
    }
  }

  out
}
