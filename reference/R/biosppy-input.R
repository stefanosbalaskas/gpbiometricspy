#' Prepare Gazepoint signals for Python BioSPPy
#'
#' Converts Gazepoint EDA/GSR or PPG/BVP waveform data into grouped numeric
#' vectors suitable for transfer to Python BioSPPy. The function validates the
#' timebase, records missing-data handling, and can write headerless one-column
#' CSV files.
#'
#' The function prepares data only. It does not invoke Python or BioSPPy and
#' does not perform physiological interpretation.
#'
#' @param data A numeric signal vector or a data frame containing EDA/GSR or
#'   PPG/BVP samples.
#' @param signal_type Signal type: `"auto"`, `"eda"`, or `"ppg"`. Numeric-vector
#'   input requires an explicit signal type.
#' @param signal_col Signal column when `data` is a data frame. If `NULL`,
#'   common Gazepoint and biosignal column names are searched.
#' @param time_col Optional numeric time column expressed in seconds. If absent,
#'   `sampling_rate_hz` must be supplied and a time vector is generated.
#' @param group_cols Optional participant, session, trial, file, or other
#'   grouping columns.
#' @param sampling_rate_hz Optional positive sampling frequency in hertz. When
#'   omitted, it is inferred separately for each group from `time_col`.
#' @param missing Missing-signal handling: `"error"`, `"interpolate"`, or
#'   `"segments"`.
#' @param irregular Handling of irregular sampling intervals: `"error"` or
#'   `"allow"`.
#' @param sampling_tolerance Maximum relative deviation from the expected sample
#'   interval before an interval is marked irregular.
#' @param min_segment_samples Minimum number of samples retained when
#'   `missing = "segments"`.
#' @param signal_units Optional descriptive signal unit, such as
#'   `"microsiemens"` or `"arbitrary"`.
#' @param output_dir Optional directory for one-column CSV files and a manifest.
#' @param prefix Filename prefix used for exported files.
#' @param write_manifest Logical. Write a manifest when `output_dir` is supplied.
#' @param overwrite Logical. Permit replacement of existing output files.
#'
#' @return An object of class `"gazepoint_biosppy_input"` containing:
#'
#' - `samples`: row-level audit table;
#' - `vectors`: named Python-ready numeric signal vectors;
#' - `sampling_rates_hz`: sampling frequency for each vector;
#' - `manifest`: vector-level preparation summary;
#' - `files`: paths written to disk;
#' - `settings`: preparation settings and Python call templates.
#'
#' @details
#' BioSPPy signal functions assume a regularly sampled one-dimensional signal
#' and a sampling frequency in hertz. When a time column is supplied, each
#' group must be strictly increasing. Sampling irregularity is assessed against
#' the supplied or inferred sampling rate.
#'
#' With `missing = "interpolate"`, non-finite signal values are replaced by
#' linear interpolation within each group. Edge values use the nearest finite
#' value. At least two finite samples are required.
#'
#' With `missing = "segments"`, each contiguous finite run is exported as a
#' separate vector. Runs shorter than `min_segment_samples` are retained in the
#' audit table but excluded from the prepared vectors.
#'
#' Exported signal files contain one numeric value per line without a header,
#' quotation marks, or row names.
#'
#' @examples
#' eda <- data.frame(
#'   participant = rep("P01", 4),
#'   time_s = c(0, 0.1, 0.2, 0.3),
#'   EDA = c(1.0, 1.1, 1.05, 1.2)
#' )
#'
#' prepared <- prepare_gazepoint_biosppy_input(
#'   eda,
#'   signal_type = "eda",
#'   group_cols = "participant"
#' )
#'
#' prepared$vectors$P01
#' prepared$sampling_rates_hz
#'
#' @seealso [run_gazepoint_biosppy_eda()],
#'   [run_gazepoint_biosppy_ppg()]
#'
#' @export
prepare_gazepoint_biosppy_input <- function(
    data,
    signal_type = c("auto", "eda", "ppg"),
    signal_col = NULL,
    time_col = NULL,
    group_cols = NULL,
    sampling_rate_hz = NULL,
    missing = c("error", "interpolate", "segments"),
    irregular = c("error", "allow"),
    sampling_tolerance = 0.05,
    min_segment_samples = 3L,
    signal_units = NULL,
    output_dir = NULL,
    prefix = "gazepoint_biosppy",
    write_manifest = TRUE,
    overwrite = FALSE) {
  signal_type <- match.arg(signal_type)
  missing <- match.arg(missing)
  irregular <- match.arg(irregular)

  .gp_biosppy_input_nonnegative_scalar(
    sampling_tolerance,
    "sampling_tolerance"
  )

  min_segment_samples <-
    .gp_biosppy_input_positive_integer(
      min_segment_samples,
      "min_segment_samples"
    )

  .gp_biosppy_input_logical_scalar(
    write_manifest,
    "write_manifest"
  )

  .gp_biosppy_input_logical_scalar(
    overwrite,
    "overwrite"
  )

  prefix <- .gp_biosppy_input_nonempty_string(
    prefix,
    "prefix"
  )

  if (!is.null(signal_units)) {
    signal_units <-
      .gp_biosppy_input_nonempty_string(
        signal_units,
        "signal_units"
      )
  }

  if (!is.null(sampling_rate_hz)) {
    .gp_biosppy_input_positive_scalar(
      sampling_rate_hz,
      "sampling_rate_hz"
    )
  }

  input <- .gp_biosppy_input_extract(
    data = data,
    signal_type = signal_type,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    sampling_rate_hz = sampling_rate_hz
  )

  samples <- input$data
  signal_type <- input$signal_type
  signal_col <- input$signal_col
  time_col <- input$time_col
  group_cols <- input$group_cols

  samples$signal_prepared <- NA_real_
  samples$finite_raw <- is.finite(samples$signal_raw)
  samples$interpolated <- FALSE
  samples$included <- FALSE
  samples$segment_id <- NA_integer_
  samples$vector_id <- NA_character_
  samples$exclusion_reason <- NA_character_

  groups <- .gp_biosppy_input_split_indices(
    samples,
    group_cols
  )

  vectors <- list()
  sampling_rates <- numeric()
  manifest_rows <- list()

  vector_counter <- 0L
  manifest_counter <- 0L

  for (group_i in seq_along(groups)) {
    idx <- groups[[group_i]]
    group_id <- names(groups)[group_i]

    group_time <- samples$time_s[idx]
    group_signal <- samples$signal_raw[idx]

    if (any(!is.finite(group_time))) {
      stop(
        "Non-finite time values were found in group `",
        group_id,
        "`.",
        call. = FALSE
      )
    }

    if (
      length(group_time) > 1L &&
        any(diff(group_time) <= 0)
    ) {
      stop(
        "Time values must be strictly increasing within group `",
        group_id,
        "`.",
        call. = FALSE
      )
    }

    timebase <- .gp_biosppy_input_timebase(
      time_s = group_time,
      sampling_rate_hz = sampling_rate_hz,
      sampling_tolerance = sampling_tolerance
    )

    group_rate <- timebase$sampling_rate_hz
    gap_irregular <- timebase$interval_irregular

    if (
      any(gap_irregular) &&
        identical(irregular, "error")
    ) {
      stop(
        "Irregular sampling intervals were found in group `",
        group_id,
        "`. Use `irregular = \"allow\"` only after reviewing the timebase.",
        call. = FALSE
      )
    }

    finite_signal <- is.finite(group_signal)

    group_values <- if (length(group_cols) > 0L) {
      samples[
        idx[1L],
        group_cols,
        drop = FALSE
      ]
    } else {
      data.frame(
        group = "all",
        stringsAsFactors = FALSE
      )
    }

    add_vector <- function(local_idx,
                           prepared_values,
                           segment_id = NA_integer_) {
      vector_counter <<- vector_counter + 1L

      vector_id <- if (is.na(segment_id)) {
        group_id
      } else {
        paste0(
          group_id,
          "__segment_",
          sprintf("%03d", segment_id)
        )
      }

      global_idx <- idx[local_idx]

      vectors[[vector_counter]] <<-
        unname(prepared_values)

      names(vectors)[vector_counter] <<-
        vector_id

      sampling_rates[vector_counter] <<-
        group_rate

      names(sampling_rates)[vector_counter] <<-
        vector_id

      samples$signal_prepared[global_idx] <<-
        prepared_values

      samples$included[global_idx] <<- TRUE
      samples$segment_id[global_idx] <<-
        segment_id

      samples$vector_id[global_idx] <<-
        vector_id

      if (identical(missing, "interpolate")) {
        samples$interpolated[global_idx] <<-
          !finite_signal[local_idx]
      }

      manifest_counter <<- manifest_counter + 1L

      manifest_row <- data.frame(
        group_id = group_id,
        vector_id = vector_id,
        segment_id = segment_id,
        signal_type = signal_type,
        source_signal_col = if (
          is.null(signal_col)
        ) {
          NA_character_
        } else {
          signal_col
        },
        signal_units = if (
          is.null(signal_units)
        ) {
          NA_character_
        } else {
          signal_units
        },
        sampling_rate_hz = group_rate,
        sample_count = length(prepared_values),
        start_time_s = group_time[local_idx[1L]],
        end_time_s =
          group_time[local_idx[length(local_idx)]],
        duration_s = if (
          length(local_idx) > 1L
        ) {
          group_time[
            local_idx[length(local_idx)]
          ] - group_time[local_idx[1L]]
        } else {
          0
        },
        raw_missing_samples_in_group =
          sum(!finite_signal),
        interpolated_samples = sum(
          !finite_signal[local_idx]
        ),
        irregular_intervals_in_group =
          sum(gap_irregular),
        maximum_relative_interval_error =
          timebase$maximum_relative_error,
        stringsAsFactors = FALSE
      )

      manifest_rows[[manifest_counter]] <<-
        cbind(
          group_values,
          manifest_row
        )

      invisible(vector_id)
    }

    if (identical(missing, "error")) {
      if (any(!finite_signal)) {
        stop(
          "Non-finite signal values were found in group `",
          group_id,
          "`. Choose `missing = \"interpolate\"` or ",
          "`missing = \"segments\"` to handle them explicitly.",
          call. = FALSE
        )
      }

      add_vector(
        local_idx = seq_along(idx),
        prepared_values = group_signal
      )

      next
    }

    if (identical(missing, "interpolate")) {
      if (sum(finite_signal) < 2L) {
        stop(
          "At least two finite signal samples are required ",
          "for interpolation in group `",
          group_id,
          "`.",
          call. = FALSE
        )
      }

      prepared <- stats::approx(
        x = group_time[finite_signal],
        y = group_signal[finite_signal],
        xout = group_time,
        method = "linear",
        rule = 2,
        ties = "ordered"
      )$y

      add_vector(
        local_idx = seq_along(idx),
        prepared_values = prepared
      )

      next
    }

    samples$exclusion_reason[
      idx[!finite_signal]
    ] <- "missing_or_nonfinite"

    local_segment <- rep(
      NA_integer_,
      length(idx)
    )

    segment_number <- 0L

    for (j in seq_along(idx)) {
      if (!finite_signal[j]) {
        next
      }

      starts_new <- j == 1L ||
        !finite_signal[j - 1L] ||
        (
          j > 1L &&
            gap_irregular[j - 1L]
        )

      if (starts_new) {
        segment_number <- segment_number + 1L
      }

      local_segment[j] <- segment_number
    }

    valid_segments <- sort(
      unique(local_segment[is.finite(local_segment)])
    )

    for (segment_id in valid_segments) {
      local_idx <- which(
        local_segment == segment_id
      )

      global_idx <- idx[local_idx]

      samples$segment_id[global_idx] <-
        segment_id

      if (length(local_idx) < min_segment_samples) {
        samples$exclusion_reason[global_idx] <-
          "short_segment"

        next
      }

      add_vector(
        local_idx = local_idx,
        prepared_values = group_signal[local_idx],
        segment_id = segment_id
      )
    }
  }

  if (length(vectors) == 0L) {
    stop(
      "No BioSPPy-ready vectors remained after preparation.",
      call. = FALSE
    )
  }

  manifest <- do.call(
    rbind,
    manifest_rows
  )

  rownames(manifest) <- NULL

  files <- .gp_biosppy_input_write_files(
    vectors = vectors,
    manifest = manifest,
    signal_type = signal_type,
    output_dir = output_dir,
    prefix = prefix,
    write_manifest = write_manifest,
    overwrite = overwrite
  )

  python_function <- if (
    identical(signal_type, "eda")
  ) {
    "biosppy.signals.eda.eda"
  } else {
    "biosppy.signals.ppg.ppg"
  }

  settings <- list(
    signal_type = signal_type,
    signal_col = signal_col,
    time_col = time_col,
    group_cols = group_cols,
    supplied_sampling_rate_hz =
      sampling_rate_hz,
    missing = missing,
    irregular = irregular,
    sampling_tolerance =
      sampling_tolerance,
    min_segment_samples =
      min_segment_samples,
    signal_units = signal_units,
    output_dir = output_dir,
    prefix = prefix,
    write_manifest = write_manifest,
    python_function = python_function,
    python_call_template = paste0(
      python_function,
      "(signal=signal, sampling_rate=fs, show=False)"
    ),
    interpretation_notes = c(
      "Prepared vectors contain raw waveform samples and are not physiological feature tables.",
      "The helper does not execute Python or BioSPPy.",
      "BioSPPy assumes regularly sampled one-dimensional signals.",
      "Interpolation and segmentation decisions are recorded in the audit table and manifest.",
      "EDA and PPG processing outputs should not be interpreted as diagnoses or direct measures of emotion, stress, or cognition."
    )
  )

  structure(
    list(
      samples = samples,
      vectors = vectors,
      sampling_rates_hz = sampling_rates,
      manifest = manifest,
      files = files,
      settings = settings
    ),
    class = c(
      "gazepoint_biosppy_input",
      "list"
    )
  )
}

.gp_biosppy_input_extract <- function(data,
                                      signal_type,
                                      signal_col,
                                      time_col,
                                      group_cols,
                                      sampling_rate_hz) {
  if (
    is.numeric(data) &&
      !is.data.frame(data)
  ) {
    if (length(data) == 0L) {
      stop(
        "`data` must contain at least one signal sample.",
        call. = FALSE
      )
    }

    if (identical(signal_type, "auto")) {
      stop(
        "Numeric-vector input requires `signal_type = \"eda\"` ",
        "or `signal_type = \"ppg\"`.",
        call. = FALSE
      )
    }

    if (is.null(sampling_rate_hz)) {
      stop(
        "`sampling_rate_hz` is required for numeric-vector input.",
        call. = FALSE
      )
    }

    if (
      !is.null(group_cols) &&
        length(group_cols) > 0L
    ) {
      stop(
        "`group_cols` cannot be used with a numeric vector.",
        call. = FALSE
      )
    }

    out <- data.frame(
      source_row = seq_along(data),
      time_s = (
        seq_along(data) - 1L
      ) / sampling_rate_hz,
      signal_raw = as.numeric(data),
      stringsAsFactors = FALSE
    )

    return(list(
      data = out,
      signal_type = signal_type,
      signal_col = NULL,
      time_col = "time_s",
      group_cols = character()
    ))
  }

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a numeric vector or data frame.",
      call. = FALSE
    )
  }

  if (nrow(data) == 0L) {
    stop(
      "`data` must contain at least one row.",
      call. = FALSE
    )
  }

  resolved <- .gp_biosppy_input_resolve_signal(
    data = data,
    signal_type = signal_type,
    signal_col = signal_col
  )

  signal_type <- resolved$signal_type
  signal_col <- resolved$signal_col

  if (!is.numeric(data[[signal_col]])) {
    stop(
      "`signal_col` must identify a numeric column.",
      call. = FALSE
    )
  }

  if (is.null(group_cols)) {
    group_cols <- character()
  } else {
    group_cols <- unique(
      as.character(group_cols)
    )
  }

  if (
    anyNA(group_cols) ||
      any(!nzchar(group_cols))
  ) {
    stop(
      "`group_cols` must contain non-empty column names.",
      call. = FALSE
    )
  }

  missing_groups <- setdiff(
    group_cols,
    names(data)
  )

  if (length(missing_groups) > 0L) {
    stop(
      "`group_cols` were not found in `data`: ",
      paste(
        missing_groups,
        collapse = ", "
      ),
      call. = FALSE
    )
  }

  if (is.null(time_col)) {
    time_col <- .gp_biosppy_input_find_candidate(
      names(data),
      c(
        "time_s",
        "TIME_S",
        "timestamp_s",
        "time_sec",
        "TIME",
        "time",
        "timestamp",
        "RecordingTime"
      )
    )
  } else {
    time_col <-
      .gp_biosppy_input_nonempty_string(
        time_col,
        "time_col"
      )

    if (!time_col %in% names(data)) {
      stop(
        "`time_col` was not found in `data`.",
        call. = FALSE
      )
    }
  }

  if (
    is.null(time_col) &&
      is.null(sampling_rate_hz)
  ) {
    stop(
      "Supply `time_col` or `sampling_rate_hz`.",
      call. = FALSE
    )
  }

  if (
    !is.null(time_col) &&
      !is.numeric(data[[time_col]])
  ) {
    stop(
      "`time_col` must identify a numeric column in seconds.",
      call. = FALSE
    )
  }

  out <- data.frame(
    source_row = seq_len(nrow(data)),
    stringsAsFactors = FALSE
  )

  if (length(group_cols) > 0L) {
    out <- cbind(
      out,
      data[group_cols]
    )
  }

  out$time_s <- if (is.null(time_col)) {
    (
      seq_len(nrow(data)) - 1L
    ) / sampling_rate_hz
  } else {
    as.numeric(data[[time_col]])
  }

  out$signal_raw <- as.numeric(
    data[[signal_col]]
  )

  list(
    data = out,
    signal_type = signal_type,
    signal_col = signal_col,
    time_col = if (
      is.null(time_col)
    ) {
      "time_s"
    } else {
      time_col
    },
    group_cols = group_cols
  )
}

.gp_biosppy_input_resolve_signal <- function(data,
                                             signal_type,
                                             signal_col) {
  eda_candidates <- c(
    "EDA",
    "GSR",
    "EDA_RAW",
    "GSR_RAW",
    "EDA_clean",
    "GSR_clean",
    "SCR",
    "signal"
  )

  ppg_candidates <- c(
    "PPG",
    "BVP",
    "HRP",
    "PULSE",
    "PPG_RAW",
    "HRP_RAW",
    "PPG_clean",
    "HRP_clean",
    "signal"
  )

  if (!is.null(signal_col)) {
    signal_col <-
      .gp_biosppy_input_nonempty_string(
        signal_col,
        "signal_col"
      )

    if (!signal_col %in% names(data)) {
      stop(
        "`signal_col` was not found in `data`.",
        call. = FALSE
      )
    }

    if (identical(signal_type, "auto")) {
      lower <- tolower(signal_col)

      eda_match <- grepl(
        "eda|gsr|scr",
        lower
      )

      ppg_match <- grepl(
        "ppg|bvp|hrp|pulse",
        lower
      )

      if (eda_match == ppg_match) {
        stop(
          "Could not infer `signal_type` from `signal_col`. ",
          "Specify `signal_type = \"eda\"` or `signal_type = \"ppg\"`.",
          call. = FALSE
        )
      }

      signal_type <- if (eda_match) {
        "eda"
      } else {
        "ppg"
      }
    }

    return(list(
      signal_type = signal_type,
      signal_col = signal_col
    ))
  }

  if (identical(signal_type, "eda")) {
    signal_col <-
      .gp_biosppy_input_find_candidate(
        names(data),
        eda_candidates
      )
  } else if (identical(signal_type, "ppg")) {
    signal_col <-
      .gp_biosppy_input_find_candidate(
        names(data),
        ppg_candidates
      )
  } else {
    eda_col <-
      .gp_biosppy_input_find_candidate(
        names(data),
        setdiff(
          eda_candidates,
          "signal"
        )
      )

    ppg_col <-
      .gp_biosppy_input_find_candidate(
        names(data),
        setdiff(
          ppg_candidates,
          "signal"
        )
      )

    if (
      !is.null(eda_col) &&
        !is.null(ppg_col)
    ) {
      stop(
        "Both EDA and PPG candidate columns were found. ",
        "Specify `signal_type` and `signal_col` explicitly.",
        call. = FALSE
      )
    }

    if (is.null(eda_col) && is.null(ppg_col)) {
      stop(
        "Could not identify an EDA/GSR or PPG/BVP signal column. ",
        "Supply `signal_type` and `signal_col` explicitly.",
        call. = FALSE
      )
    }

    if (!is.null(eda_col)) {
      signal_type <- "eda"
      signal_col <- eda_col
    } else {
      signal_type <- "ppg"
      signal_col <- ppg_col
    }
  }

  if (is.null(signal_col)) {
    stop(
      "Could not identify a signal column for `signal_type = \"",
      signal_type,
      "\"`.",
      call. = FALSE
    )
  }

  list(
    signal_type = signal_type,
    signal_col = signal_col
  )
}

.gp_biosppy_input_find_candidate <- function(names_vector,
                                             candidates) {
  lower_names <- tolower(names_vector)

  for (candidate in candidates) {
    hit <- which(
      lower_names == tolower(candidate)
    )

    if (length(hit) > 0L) {
      return(names_vector[hit[1L]])
    }
  }

  NULL
}

.gp_biosppy_input_split_indices <- function(data,
                                            group_cols) {
  if (length(group_cols) == 0L) {
    return(list(
      all = seq_len(nrow(data))
    ))
  }

  grouping <- data[group_cols]

  grouping[] <- lapply(
    grouping,
    function(x) {
      x <- as.character(x)
      x[is.na(x)] <- "<NA>"
      x
    }
  )

  key <- do.call(
    paste,
    c(
      grouping,
      sep = "||"
    )
  )

  split(
    seq_len(nrow(data)),
    factor(
      key,
      levels = unique(key)
    ),
    drop = TRUE
  )
}

.gp_biosppy_input_timebase <- function(time_s,
                                       sampling_rate_hz,
                                       sampling_tolerance) {
  if (length(time_s) < 2L) {
    if (is.null(sampling_rate_hz)) {
      stop(
        "A sampling rate cannot be inferred from fewer than two samples.",
        call. = FALSE
      )
    }

    return(list(
      sampling_rate_hz = sampling_rate_hz,
      interval_irregular = logical(),
      maximum_relative_error = 0
    ))
  }

  intervals <- diff(time_s)

  inferred_rate <- 1 / stats::median(
    intervals
  )

  resolved_rate <- if (
    is.null(sampling_rate_hz)
  ) {
    inferred_rate
  } else {
    sampling_rate_hz
  }

  if (
    !is.finite(resolved_rate) ||
      resolved_rate <= 0
  ) {
    stop(
      "Could not resolve a positive sampling rate.",
      call. = FALSE
    )
  }

  expected_interval <- 1 / resolved_rate

  relative_error <- abs(
    intervals - expected_interval
  ) / expected_interval

  list(
    sampling_rate_hz = resolved_rate,
    interval_irregular =
      relative_error > sampling_tolerance,
    maximum_relative_error = max(
      relative_error,
      na.rm = TRUE
    )
  )
}

.gp_biosppy_input_write_files <- function(vectors,
                                          manifest,
                                          signal_type,
                                          output_dir,
                                          prefix,
                                          write_manifest,
                                          overwrite) {
  if (is.null(output_dir)) {
    return(data.frame(
      file_type = character(),
      vector_id = character(),
      path = character(),
      stringsAsFactors = FALSE
    ))
  }

  output_dir <-
    .gp_biosppy_input_nonempty_string(
      output_dir,
      "output_dir"
    )

  dir.create(
    output_dir,
    recursive = TRUE,
    showWarnings = FALSE
  )

  if (!dir.exists(output_dir)) {
    stop(
      "Could not create `output_dir`.",
      call. = FALSE
    )
  }

  safe_prefix <- .gp_biosppy_input_safe_name(
    prefix
  )

  filenames <- character(
    length(vectors)
  )

  used_names <- character()

  for (i in seq_along(vectors)) {
    filename <- paste0(
      safe_prefix,
      "_",
      signal_type,
      "_",
      .gp_biosppy_input_safe_name(
        names(vectors)[i]
      ),
      ".csv"
    )

    if (filename %in% used_names) {
      filename <- paste0(
        tools::file_path_sans_ext(
          filename
        ),
        "_",
        i,
        ".csv"
      )
    }

    filenames[i] <- filename
    used_names <- c(
      used_names,
      filename
    )
  }

  vector_paths <- file.path(
    output_dir,
    filenames
  )

  manifest_path <- if (
    isTRUE(write_manifest)
  ) {
    file.path(
      output_dir,
      paste0(
        safe_prefix,
        "_",
        signal_type,
        "_manifest.csv"
      )
    )
  } else {
    character()
  }

  candidate_paths <- c(
    vector_paths,
    manifest_path
  )

  existing <- candidate_paths[
    file.exists(candidate_paths)
  ]

  if (
    length(existing) > 0L &&
      !isTRUE(overwrite)
  ) {
    stop(
      "Output file already exists: ",
      existing[1L],
      ". Use `overwrite = TRUE` to replace it.",
      call. = FALSE
    )
  }

  files <- vector(
    "list",
    length(vectors) +
      as.integer(isTRUE(write_manifest))
  )

  counter <- 0L

  for (i in seq_along(vectors)) {
    utils::write.table(
      data.frame(
        signal = vectors[[i]]
      ),
      file = vector_paths[i],
      sep = ",",
      row.names = FALSE,
      col.names = FALSE,
      quote = FALSE,
      na = ""
    )

    counter <- counter + 1L

    files[[counter]] <- data.frame(
      file_type = "signal",
      vector_id = names(vectors)[i],
      path = normalizePath(
        vector_paths[i],
        winslash = "/",
        mustWork = FALSE
      ),
      stringsAsFactors = FALSE
    )
  }

  if (isTRUE(write_manifest)) {
    utils::write.csv(
      manifest,
      manifest_path,
      row.names = FALSE,
      na = ""
    )

    counter <- counter + 1L

    files[[counter]] <- data.frame(
      file_type = "manifest",
      vector_id = NA_character_,
      path = normalizePath(
        manifest_path,
        winslash = "/",
        mustWork = FALSE
      ),
      stringsAsFactors = FALSE
    )
  }

  out <- do.call(
    rbind,
    files
  )

  rownames(out) <- NULL
  out
}

.gp_biosppy_input_safe_name <- function(x) {
  x <- as.character(x)

  if (
    length(x) != 1L ||
      is.na(x)
  ) {
    x <- "group"
  }

  out <- gsub(
    "[^A-Za-z0-9._-]+",
    "_",
    x
  )

  out <- gsub(
    "^_+|_+$",
    "",
    out
  )

  if (!nzchar(out)) {
    out <- "group"
  }

  out
}

.gp_biosppy_input_positive_scalar <- function(x,
                                              argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x <= 0
  ) {
    stop(
      "`",
      argument,
      "` must be one positive finite number.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_biosppy_input_nonnegative_scalar <- function(x,
                                                 argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x < 0
  ) {
    stop(
      "`",
      argument,
      "` must be one non-negative finite number.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_biosppy_input_positive_integer <- function(x,
                                               argument) {
  if (
    !is.numeric(x) ||
      length(x) != 1L ||
      !is.finite(x) ||
      x < 1 ||
      x != as.integer(x)
  ) {
    stop(
      "`",
      argument,
      "` must be one positive integer.",
      call. = FALSE
    )
  }

  as.integer(x)
}

.gp_biosppy_input_logical_scalar <- function(x,
                                             argument) {
  if (
    !is.logical(x) ||
      length(x) != 1L ||
      is.na(x)
  ) {
    stop(
      "`",
      argument,
      "` must be TRUE or FALSE.",
      call. = FALSE
    )
  }

  invisible(x)
}

.gp_biosppy_input_nonempty_string <- function(x,
                                              argument) {
  x <- as.character(x)

  if (
    length(x) != 1L ||
      is.na(x) ||
      !nzchar(trimws(x))
  ) {
    stop(
      "`",
      argument,
      "` must be one non-empty character value.",
      call. = FALSE
    )
  }

  x
}
