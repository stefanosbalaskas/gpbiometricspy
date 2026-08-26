#' Standardise a Gazepoint plot return contract
#'
#' Adds consistent attributes to a ggplot object so plotting helpers can be
#' tested and reused in automated reports.
#'
#' @param plot A ggplot object.
#' @param plot_data Optional data frame used to create the plot.
#' @param settings Optional list of plot settings.
#' @param interpretation_notes Optional character vector of interpretation notes.
#' @param plot_type Optional short plot-type label.
#'
#' @return A ggplot object with standardized attributes.
#' @export
standardise_gazepoint_plot_contract <- function(plot,
                                                plot_data = NULL,
                                                settings = list(),
                                                interpretation_notes = NULL,
                                                plot_type = NULL) {
  gpbiometrics_require_ggplot2()

  if (!inherits(plot, "ggplot")) {
    stop("`plot` must be a ggplot object.", call. = FALSE)
  }

  if (!is.null(plot_data) && !is.data.frame(plot_data)) {
    stop("`plot_data` must be NULL or a data frame.", call. = FALSE)
  }

  if (!is.list(settings)) {
    stop("`settings` must be a list.", call. = FALSE)
  }

  if (!is.null(interpretation_notes) && !is.character(interpretation_notes)) {
    stop("`interpretation_notes` must be NULL or a character vector.", call. = FALSE)
  }

  if (!is.null(plot_type) &&
      (!is.character(plot_type) || length(plot_type) != 1 || is.na(plot_type))) {
    stop("`plot_type` must be NULL or a single character value.", call. = FALSE)
  }

  if (is.null(plot_data) && is.data.frame(attr(plot, "plot_data"))) {
    plot_data <- attr(plot, "plot_data")
  }

  if (length(settings) == 0 && is.list(attr(plot, "settings"))) {
    settings <- attr(plot, "settings")
  }

  if (is.null(interpretation_notes)) {
    existing_notes <- attr(plot, "interpretation_notes")

    if (is.character(existing_notes)) {
      interpretation_notes <- existing_notes
    } else if (is.list(settings) &&
               "interpretation_notes" %in% names(settings) &&
               is.character(settings$interpretation_notes)) {
      interpretation_notes <- settings$interpretation_notes
    } else {
      interpretation_notes <- character()
    }
  }

  if (is.null(plot_type) &&
      is.list(settings) &&
      "plot_type" %in% names(settings) &&
      is.character(settings$plot_type) &&
      length(settings$plot_type) == 1) {
    plot_type <- settings$plot_type
  }

  attr(plot, "plot_data") <- plot_data
  attr(plot, "settings") <- settings
  attr(plot, "interpretation_notes") <- interpretation_notes
  attr(plot, "plot_type") <- plot_type
  attr(plot, "gazepoint_plot_contract") <- TRUE

  if (!inherits(plot, "gazepoint_plot")) {
    class(plot) <- c("gazepoint_plot", class(plot))
  }

  plot
}

#' Check a Gazepoint plot return contract
#'
#' Checks whether an object follows the package's plotting return convention.
#'
#' @param plot A plot object.
#' @param require_plot_data Logical. If `TRUE`, `plot_data` must be present.
#' @param require_settings Logical. If `TRUE`, `settings` must be present.
#'
#' @return A list with `overview`, `checks`, `plot_data`, and `settings`.
#' @export
check_gazepoint_plot_contract <- function(plot,
                                          require_plot_data = TRUE,
                                          require_settings = TRUE) {
  if (!is.logical(require_plot_data) ||
      length(require_plot_data) != 1 ||
      is.na(require_plot_data)) {
    stop("`require_plot_data` must be TRUE or FALSE.", call. = FALSE)
  }

  if (!is.logical(require_settings) ||
      length(require_settings) != 1 ||
      is.na(require_settings)) {
    stop("`require_settings` must be TRUE or FALSE.", call. = FALSE)
  }

  is_ggplot <- inherits(plot, "ggplot")
  is_gazepoint_plot <- inherits(plot, "gazepoint_plot") ||
    isTRUE(attr(plot, "gazepoint_plot_contract"))

  plot_data <- attr(plot, "plot_data")
  settings <- attr(plot, "settings")
  interpretation_notes <- attr(plot, "interpretation_notes")
  plot_type <- attr(plot, "plot_type")

  has_plot_data <- is.data.frame(plot_data)
  has_settings <- is.list(settings)
  has_notes <- is.character(interpretation_notes)
  has_plot_type <- !is.null(plot_type) &&
    is.character(plot_type) &&
    length(plot_type) == 1 &&
    !is.na(plot_type)

  checks <- data.frame(
    check = c(
      "is_ggplot",
      "is_gazepoint_plot",
      "has_plot_data",
      "has_settings",
      "has_interpretation_notes",
      "has_plot_type"
    ),
    passed = c(
      is_ggplot,
      is_gazepoint_plot,
      has_plot_data,
      has_settings,
      has_notes,
      has_plot_type
    ),
    required = c(
      TRUE,
      FALSE,
      require_plot_data,
      require_settings,
      FALSE,
      FALSE
    ),
    stringsAsFactors = FALSE
  )

  required_failed <- checks$required & !checks$passed

  overview <- data.frame(
    is_ggplot = is_ggplot,
    is_gazepoint_plot = is_gazepoint_plot,
    has_plot_data = has_plot_data,
    plot_data_rows = if (has_plot_data) nrow(plot_data) else NA_integer_,
    has_settings = has_settings,
    has_interpretation_notes = has_notes,
    has_plot_type = has_plot_type,
    status = if (any(required_failed)) {
      "fail_plot_contract"
    } else if (!is_gazepoint_plot || !has_notes || !has_plot_type) {
      "warn_partial_plot_contract"
    } else {
      "pass_plot_contract"
    },
    stringsAsFactors = FALSE
  )

  structure(
    list(
      overview = overview,
      checks = checks,
      plot_data = if (has_plot_data) plot_data else data.frame(),
      settings = if (has_settings) settings else list()
    ),
    class = c("gazepoint_plot_contract_check", "list")
  )
}

#' Extract stored plot data
#'
#' @param plot A plot object returned by a gpbiometrics plotting helper.
#'
#' @return A data frame.
#' @export
get_gazepoint_plot_data <- function(plot) {
  plot_data <- attr(plot, "plot_data")

  if (!is.data.frame(plot_data)) {
    stop("No `plot_data` data frame is stored on this plot object.", call. = FALSE)
  }

  plot_data
}

#' Extract stored plot settings
#'
#' @param plot A plot object returned by a gpbiometrics plotting helper.
#'
#' @return A list.
#' @export
get_gazepoint_plot_settings <- function(plot) {
  settings <- attr(plot, "settings")

  if (!is.list(settings)) {
    stop("No `settings` list is stored on this plot object.", call. = FALSE)
  }

  settings
}
