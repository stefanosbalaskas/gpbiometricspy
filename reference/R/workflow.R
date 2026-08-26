#' Run a Gazepoint Biometrics workflow
#'
#' Runs a compact end-to-end workflow for Gazepoint Biometrics exports. The
#' workflow imports rectangular all-gaze/fixation-style CSV exports from a
#' folder, validates biometric columns, detects active channels, audits
#' missingness, signal quality, sampling/timing, optionally creates window-level
#' summaries, creates optional biometric exclusion recommendations, extracts
#' optional TTL marker events, and produces checklist and methods-text outputs.
#'
#' @param path Folder containing Gazepoint CSV exports.
#' @param group_columns Optional columns used to create multimodal window
#'   summaries, such as `c("source_participant", "MEDIA_ID")`.
#' @param recursive Should subfolders be searched?
#' @param include_fixations Should fixation files be imported? Defaults to
#'   `FALSE` because continuous biometric summaries should usually be computed
#'   from all-gaze sample-level exports rather than fixation-level exports.
#' @param include_all_gaze Should all-gaze files be imported?
#' @param include_other_csv Should other non-Data-Summary CSV files be attempted?
#' @param require_active_signal Logical. Should inactive biometric signals be
#'   flagged in validation/checklist outputs?
#' @param create_exclusion_recommendations Logical. Should window-level and
#'   participant-level keep/review/exclude recommendations be created when
#'   `group_columns` are supplied?
#' @param gsr_min_usable_pct Minimum acceptable usable percentage for GSR/EDA
#'   windows.
#' @param hr_min_usable_pct Minimum acceptable usable percentage for heart-rate
#'   windows.
#' @param dial_min_usable_pct Minimum acceptable usable percentage for
#'   engagement-dial windows.
#' @param extract_ttl_events Logical. Should TTL marker events be extracted?
#' @param ttl_event_mode TTL event extraction mode passed to
#'   `extract_gazepoint_ttl_events()`. Use `"changes"` or `"nonzero"`.
#' @param audit_sampling Logical. Should sampling/timing information be audited?
#' @param sampling_group_columns Optional columns for the sampling audit. If
#'   `NULL`, the workflow uses available file/participant/media columns.
#' @param sampling_time_column Optional time/order column for the sampling audit.
#' @param sampling_time_unit Unit of the selected time/order column. Use
#'   `"seconds"`, `"milliseconds"`, `"microseconds"`, or `"samples"`.
#' @param expected_sampling_rate_hz Optional expected sampling rate in Hz.
#'
#' @return A list with imported data, validation outputs, missingness summaries,
#'   quality audits, sampling/timing audits, optional window summaries, optional
#'   exclusion recommendations, optional TTL events, checklist, and methods
#'   text. The object has class `"gazepoint_biometrics_workflow"`.
#'
#' @export
run_gazepoint_biometrics_workflow <- function(path,
                                              group_columns = NULL,
                                              recursive = FALSE,
                                              include_fixations = FALSE,
                                              include_all_gaze = TRUE,
                                              include_other_csv = FALSE,
                                              require_active_signal = TRUE,
                                              create_exclusion_recommendations = TRUE,
                                              gsr_min_usable_pct = 50,
                                              hr_min_usable_pct = 50,
                                              dial_min_usable_pct = 50,
                                              extract_ttl_events = TRUE,
                                              ttl_event_mode = c("changes", "nonzero"),
                                              audit_sampling = TRUE,
                                              sampling_group_columns = NULL,
                                              sampling_time_column = NULL,
                                              sampling_time_unit = c(
                                                "samples",
                                                "seconds",
                                                "milliseconds",
                                                "microseconds"
                                              ),
                                              expected_sampling_rate_hz = 60) {
  ttl_event_mode <- match.arg(ttl_event_mode)
  sampling_time_unit <- match.arg(sampling_time_unit)

  data <- import_gazepoint_biometric_folder(
    path = path,
    recursive = recursive,
    include_fixations = include_fixations,
    include_all_gaze = include_all_gaze,
    include_other_csv = include_other_csv
  )

  validation <- validate_gazepoint_biometrics(
    data,
    require_active_signal = require_active_signal
  )

  missingness <- audit_gazepoint_biometric_missingness(data)

  quality <- combine_gazepoint_tables(list(
    audit_gazepoint_gsr_quality(data),
    audit_gazepoint_hr_quality(data),
    audit_gazepoint_engagement_dial(data)
  ))

  sampling <- NULL

  if (isTRUE(audit_sampling)) {
    if (is.null(sampling_group_columns)) {
      sampling_group_columns <- intersect(
        c("source_file", "source_participant", "MEDIA_ID", "MEDIA_NAME"),
        names(data)
      )
    }

    sampling <- audit_gazepoint_biometric_sampling(
      data = data,
      group_columns = sampling_group_columns,
      time_column = sampling_time_column,
      time_unit = sampling_time_unit,
      expected_rate_hz = expected_sampling_rate_hz
    )
  }

  windows <- NULL
  exclusion_recommendations <- NULL

  if (!is.null(group_columns)) {
    windows <- summarise_gazepoint_multimodal_windows(
      data = data,
      group_columns = group_columns
    )

    if (isTRUE(create_exclusion_recommendations)) {
      exclusion_recommendations <- recommend_gazepoint_biometric_exclusions(
        data = windows,
        data_is_window_summary = TRUE,
        gsr_min_usable_pct = gsr_min_usable_pct,
        hr_min_usable_pct = hr_min_usable_pct,
        dial_min_usable_pct = dial_min_usable_pct
      )
    }
  }

  ttl_events <- NULL

  if (isTRUE(extract_ttl_events)) {
    ttl_group_columns <- intersect(
      c("source_participant", "USER", "USERID", "MEDIA_ID", "MEDIA_NAME"),
      names(data)
    )

    ttl_events <- extract_gazepoint_ttl_events(
      data = data,
      group_columns = ttl_group_columns,
      mode = ttl_event_mode
    )
  }

  checklist <- create_gazepoint_biometrics_checklist(
    data,
    require_active_signal = require_active_signal
  )

  methods_text <- create_gazepoint_biometrics_methods_text(
    checklist = checklist
  )

  overview <- data.frame(
    n_rows = nrow(data),
    n_columns = ncol(data),
    source_file_count = length(unique(data$source_file)),
    has_sampling_audit = !is.null(sampling),
    sampling_group_count = ifelse(is.null(sampling), NA_integer_, nrow(sampling)),
    has_window_summaries = !is.null(windows),
    has_exclusion_recommendations = !is.null(exclusion_recommendations),
    has_ttl_events = !is.null(ttl_events),
    ttl_event_count = ifelse(is.null(ttl_events), NA_integer_, nrow(ttl_events)),
    validation_issue_count = nrow(validation$issues),
    active_signal_count = validation$overview$active_signal_count,
    stringsAsFactors = FALSE
  )

  out <- list(
    overview = overview,
    data = data,
    validation = validation,
    missingness = missingness,
    quality = quality,
    sampling = sampling,
    windows = windows,
    exclusion_recommendations = exclusion_recommendations,
    ttl_events = ttl_events,
    checklist = checklist,
    methods_text = methods_text
  )

  class(out) <- c("gazepoint_biometrics_workflow", "list")
  out
}


#' Summarise a Gazepoint Biometrics workflow object
#'
#' Creates a compact summary table from an object returned by
#' `run_gazepoint_biometrics_workflow()`.
#'
#' @param workflow A workflow object returned by
#'   `run_gazepoint_biometrics_workflow()`.
#'
#' @return A one-row data frame summarising the workflow.
#'
#' @export
summarise_gazepoint_biometrics_workflow <- function(workflow) {
  if (!inherits(workflow, "gazepoint_biometrics_workflow")) {
    stop(
      "`workflow` must be produced by run_gazepoint_biometrics_workflow().",
      call. = FALSE
    )
  }

  active_channels <- workflow$validation$active_channels

  data.frame(
    n_rows = workflow$overview$n_rows,
    n_columns = workflow$overview$n_columns,
    source_file_count = workflow$overview$source_file_count,
    validation_issue_count = workflow$overview$validation_issue_count,
    active_gsr_eda = is_signal_active(active_channels, "gsr_eda"),
    active_heart_rate = is_signal_active(active_channels, "heart_rate"),
    active_engagement_dial = is_signal_active(active_channels, "engagement_dial"),
    active_ttl_marker = is_signal_active(active_channels, "ttl_marker"),
    has_sampling_audit = workflow$overview$has_sampling_audit,
    sampling_group_count = workflow$overview$sampling_group_count,
    has_window_summaries = workflow$overview$has_window_summaries,
    has_exclusion_recommendations = workflow$overview$has_exclusion_recommendations,
    has_ttl_events = workflow$overview$has_ttl_events,
    ttl_event_count = workflow$overview$ttl_event_count,
    stringsAsFactors = FALSE
  )
}
