#' Prepare Gazepoint IBI/RR data for RHRV
#'
#' Backward-compatible alias for [export_gazepoint_rhrv_input()]. This helper
#' prepares analysis-ready inter-beat interval input for optional RHRV workflows.
#' It does not call RHRV and does not derive HRV from Gazepoint's raw `HRV`
#' field. HRV features should be derived from genuine IBI/RR intervals.
#'
#' @inheritParams export_gazepoint_rhrv_input
#'
#' @return A list returned by [export_gazepoint_rhrv_input()].
#' @export
prepare_gazepoint_rhrv_input <- function(data,
                                         ibi_col = "IBI_clean_ms",
                                         group_cols = NULL,
                                         unit = c("auto", "ms", "seconds"),
                                         collapse_repeated_intervals = TRUE,
                                         repeated_tolerance_ms = 1e-8,
                                         min_ibi_ms = 300,
                                         max_ibi_ms = 2000,
                                         output_dir = NULL,
                                         prefix = "gazepoint_rhrv") {
  unit <- match.arg(unit)

  export_gazepoint_rhrv_input(
    data = data,
    ibi_col = ibi_col,
    group_cols = group_cols,
    unit = unit,
    collapse_repeated_intervals = collapse_repeated_intervals,
    repeated_tolerance_ms = repeated_tolerance_ms,
    min_ibi_ms = min_ibi_ms,
    max_ibi_ms = max_ibi_ms,
    output_dir = output_dir,
    prefix = prefix
  )
}

#' Standardize Gazepoint plot return contracts
#'
#' US-spelling compatibility wrapper around
#' [standardise_gazepoint_plot_contract()]. The wrapper accepts either a single
#' ggplot object or a list of ggplot objects. For a list of plots, `plot_data`,
#' `settings`, `interpretation_notes`, and `plot_type` may be supplied either as
#' single values applied to all plots or as same-length lists/vectors applied
#' elementwise.
#'
#' @param plot A ggplot object, or a list of ggplot objects.
#' @param plot_data Optional data frame, or a list of data frames when `plot` is
#'   a list.
#' @param settings Optional settings list, or a list of settings lists when
#'   `plot` is a list.
#' @param interpretation_notes Optional character vector, or a list/character
#'   vector of notes when `plot` is a list.
#' @param plot_type Optional plot-type label, or a character vector/list of
#'   labels when `plot` is a list.
#'
#' @return A standardized ggplot object, or a list of standardized ggplot
#'   objects.
#' @export
standardize_gazepoint_plot_contracts <- function(plot,
                                                 plot_data = NULL,
                                                 settings = list(),
                                                 interpretation_notes = NULL,
                                                 plot_type = NULL) {
  if (inherits(plot, "ggplot")) {
    return(standardise_gazepoint_plot_contract(
      plot = plot,
      plot_data = plot_data,
      settings = settings,
      interpretation_notes = interpretation_notes,
      plot_type = plot_type
    ))
  }

  if (!is.list(plot)) {
    stop("`plot` must be a ggplot object or a list of ggplot objects.", call. = FALSE)
  }

  n_plots <- length(plot)

  if (n_plots == 0) {
    return(list())
  }

  out <- lapply(seq_along(plot), function(i) {
    standardise_gazepoint_plot_contract(
      plot = plot[[i]],
      plot_data = gpbiometrics_alias_select_element(plot_data, i, n_plots),
      settings = gpbiometrics_alias_select_element(settings, i, n_plots),
      interpretation_notes = gpbiometrics_alias_select_element(
        interpretation_notes,
        i,
        n_plots
      ),
      plot_type = gpbiometrics_alias_select_element(plot_type, i, n_plots)
    )
  })

  names(out) <- names(plot)
  out
}

gpbiometrics_alias_select_element <- function(x, i, n) {
  if (is.null(x)) {
    return(NULL)
  }

  if (is.data.frame(x)) {
    return(x)
  }

  if (is.character(x) && length(x) == n) {
    return(x[[i]])
  }

  if (is.list(x) && length(x) == n) {
    return(x[[i]])
  }

  x
}
