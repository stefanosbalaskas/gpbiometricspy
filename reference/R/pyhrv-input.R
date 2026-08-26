#' Prepare Gazepoint intervals for Python pyHRV
#'
#' Converts Gazepoint inter-beat or RR intervals into millisecond NN-interval
#' vectors suitable for transfer to Python pyHRV workflows. The function does
#' not invoke Python or pyHRV.
#'
#' Input rows are retained in an auditable interval table. Missing,
#' non-positive, implausible, and repeated intervals are flagged explicitly
#' rather than removed silently.
#'
#' @param data A numeric interval vector or a data frame containing an IBI,
#'   RR, or NN-interval column.
#' @param ibi_col Interval column when `data` is a data frame. If `NULL`,
#'   common Gazepoint, RR, and NNI column names are searched.
#' @param group_cols Optional participant, session, trial, or file columns.
#'   One pyHRV-ready vector is produced per group.
#' @param unit Input interval unit: `"auto"`, `"milliseconds"`, or
#'   `"seconds"`.
#' @param filter Which intervals should be included in the pyHRV vectors:
#'   `"none"` retains all finite positive intervals, whereas `"plausible"`
#'   also applies `min_nni_ms` and `max_nni_ms`.
#' @param min_nni_ms Minimum plausible NN interval in milliseconds.
#' @param max_nni_ms Maximum plausible NN interval in milliseconds.
#' @param collapse_repeated_intervals Logical. If `TRUE`, consecutive interval
#'   values equal within `repeated_tolerance_ms` are represented once. This can
#'   be useful for sample-level Gazepoint exports in which the current IBI is
#'   repeated across multiple rows.
#' @param repeated_tolerance_ms Non-negative tolerance used to identify
#'   consecutive repeated intervals.
#' @param output_dir Optional directory in which one-column CSV files and a
#'   manifest are written.
#' @param prefix Filename prefix used when `output_dir` is supplied.
#' @param write_manifest Logical. If `TRUE` and `output_dir` is supplied,
#'   write a group-level manifest CSV.
#' @param overwrite Logical. If `FALSE`, existing output files are protected.
#'
#' @return An object of class `"gazepoint_pyhrv_input"` containing:
#'
#' - `intervals`: auditable row-level interval table;
#' - `vectors`: named list of pyHRV-ready numeric millisecond vectors;
#' - `manifest`: group-level interval and exclusion summary;
#' - `files`: paths written when `output_dir` is supplied;
#' - `settings`: complete preparation settings.
#'
#' @details
#' Automatic unit assessment first examines the interval-column name. Names
#' containing common millisecond markers are interpreted as milliseconds.
#' Otherwise, the median positive interval is used: values no greater than 10
#' are interpreted as seconds, and values at least 100 as milliseconds.
#' Intermediate values are considered ambiguous and require an explicit unit.
#'
#' CSV interval files contain one numeric millisecond value per line, without
#' row names, quotation marks, or a header. They can therefore be read into
#' Python as a one-dimensional numeric vector.
#'
#' Repeated-interval collapsing is optional because physiologically genuine
#' adjacent intervals may occasionally have identical values. The setting
#' should be chosen according to the structure of the source export.
#'
#' @examples
#' ibi <- data.frame(
#'   participant = c("P01", "P01", "P01"),
#'   IBI_clean_ms = c(800, 810, 790)
#' )
#'
#' prepared <- prepare_gazepoint_pyhrv_input(
#'   ibi,
#'   group_cols = "participant"
#' )
#'
#' prepared$vectors$P01
#' prepared$manifest
#'
#' @seealso [run_gazepoint_pyhrv_style()],
#'   [check_gazepoint_pyhrv_interval()],
#'   [prepare_gazepoint_rhrv_input()]
#'
#' @export
prepare_gazepoint_pyhrv_input <- function(
    data,
    ibi_col = NULL,
    group_cols = NULL,
    unit = c("auto", "milliseconds", "seconds"),
    filter = c("none", "plausible"),
    min_nni_ms = 300,
    max_nni_ms = 2000,
    collapse_repeated_intervals = FALSE,
    repeated_tolerance_ms = 1e-8,
    output_dir = NULL,
    prefix = "gazepoint_pyhrv",
    write_manifest = TRUE,
    overwrite = FALSE) {
  unit <- match.arg(unit)
  filter <- match.arg(filter)

  .gp_pyhrv_input_positive_scalar(
    min_nni_ms,
    "min_nni_ms"
  )

  .gp_pyhrv_input_positive_scalar(
    max_nni_ms,
    "max_nni_ms"
  )

  if (max_nni_ms <= min_nni_ms) {
    stop(
      "`max_nni_ms` must be greater than `min_nni_ms`.",
      call. = FALSE
    )
  }

  .gp_pyhrv_input_nonnegative_scalar(
    repeated_tolerance_ms,
    "repeated_tolerance_ms"
  )

  .gp_pyhrv_input_logical_scalar(
    collapse_repeated_intervals,
    "collapse_repeated_intervals"
  )

  .gp_pyhrv_input_logical_scalar(
    write_manifest,
    "write_manifest"
  )

  .gp_pyhrv_input_logical_scalar(
    overwrite,
    "overwrite"
  )

  prefix <- .gp_pyhrv_input_nonempty_string(
    prefix,
    "prefix"
  )

  input <- .gp_pyhrv_input_extract(
    data = data,
    ibi_col = ibi_col,
    group_cols = group_cols
  )

  interval_data <- input$data
  ibi_col <- input$ibi_col
  group_cols <- input$group_cols

  unit_assessment <- .gp_pyhrv_input_resolve_unit(
    values = interval_data$.interval_raw,
    unit = unit,
    column_name = ibi_col
  )

  nni_ms <- if (
    identical(
      unit_assessment$resolved_unit,
      "seconds"
    )
  ) {
    interval_data$.interval_raw * 1000
  } else {
    interval_data$.interval_raw
  }

  interval_status <- rep(
    "plausible",
    length(nni_ms)
  )

  interval_status[
    !is.finite(nni_ms)
  ] <- "missing_or_nonfinite"

  interval_status[
    is.finite(nni_ms) &
      nni_ms <= 0
  ] <- "non_positive"

  interval_status[
    is.finite(nni_ms) &
      nni_ms > 0 &
      nni_ms < min_nni_ms
  ] <- "below_minimum"

  interval_status[
    is.finite(nni_ms) &
      nni_ms > max_nni_ms
  ] <- "above_maximum"

  included <- is.finite(nni_ms) &
    nni_ms > 0

  if (identical(filter, "plausible")) {
    included <- included &
      nni_ms >= min_nni_ms &
      nni_ms <= max_nni_ms
  }

  exclusion_reason <- rep(
    NA_character_,
    length(nni_ms)
  )

  exclusion_reason[
    !is.finite(nni_ms)
  ] <- "missing_or_nonfinite"

  exclusion_reason[
    is.finite(nni_ms) &
      nni_ms <= 0
  ] <- "non_positive"

  if (identical(filter, "plausible")) {
    exclusion_reason[
      is.finite(nni_ms) &
        nni_ms > 0 &
        nni_ms < min_nni_ms
    ] <- "below_minimum"

    exclusion_reason[
      is.finite(nni_ms) &
        nni_ms > max_nni_ms
    ] <- "above_maximum"
  }

  groups <- .gp_pyhrv_input_split_indices(
    interval_data,
    group_cols
  )

  repeated <- rep(
    FALSE,
    length(nni_ms)
  )

  for (idx in groups) {
    if (length(idx) < 2L) {
      next
    }

    current <- nni_ms[idx]

    adjacent_equal <- rep(
      FALSE,
      length(idx)
    )

    adjacent_equal[-1L] <-
      is.finite(current[-1L]) &
      is.finite(current[-length(current)]) &
      abs(
        current[-1L] -
          current[-length(current)]
      ) <= repeated_tolerance_ms

    repeated[idx] <- adjacent_equal
  }

  if (isTRUE(collapse_repeated_intervals)) {
    repeated_included <- repeated &
      included

    included[repeated_included] <- FALSE

    exclusion_reason[repeated_included] <-
      "repeated_interval"
  }

  intervals <- interval_data[
    ,
    setdiff(
      names(interval_data),
      ".interval_raw"
    ),
    drop = FALSE
  ]

  intervals$nni_ms <- nni_ms
  intervals$interval_status <- interval_status
  intervals$repeated_interval <- repeated
  intervals$included <- included
  intervals$exclusion_reason <- exclusion_reason
  intervals$interval_index <- NA_integer_
  intervals$interval_end_time_s <- NA_real_

  vectors <- vector(
    "list",
    length(groups)
  )

  names(vectors) <- names(groups)

  manifest_rows <- vector(
    "list",
    length(groups)
  )

  for (group_i in seq_along(groups)) {
    idx <- groups[[group_i]]
    retained_idx <- idx[included[idx]]
    retained_values <- nni_ms[retained_idx]

    vectors[[group_i]] <- unname(
      retained_values
    )

    if (length(retained_idx) > 0L) {
      intervals$interval_index[retained_idx] <-
        seq_along(retained_idx)

      intervals$interval_end_time_s[retained_idx] <-
        cumsum(retained_values) / 1000
    }

    group_values <- if (
      length(group_cols) > 0L
    ) {
      intervals[
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

    manifest_row <- data.frame(
      group_id = names(groups)[group_i],
      input_rows = length(idx),
      finite_positive_rows = sum(
        is.finite(nni_ms[idx]) &
          nni_ms[idx] > 0
      ),
      plausible_rows = sum(
        interval_status[idx] ==
          "plausible"
      ),
      repeated_rows = sum(
        repeated[idx]
      ),
      included_intervals = sum(
        included[idx]
      ),
      excluded_intervals = sum(
        !included[idx]
      ),
      excluded_missing_or_nonfinite = sum(
        exclusion_reason[idx] ==
          "missing_or_nonfinite",
        na.rm = TRUE
      ),
      excluded_non_positive = sum(
        exclusion_reason[idx] ==
          "non_positive",
        na.rm = TRUE
      ),
      excluded_below_minimum = sum(
        exclusion_reason[idx] ==
          "below_minimum",
        na.rm = TRUE
      ),
      excluded_above_maximum = sum(
        exclusion_reason[idx] ==
          "above_maximum",
        na.rm = TRUE
      ),
      excluded_repeated = sum(
        exclusion_reason[idx] ==
          "repeated_interval",
        na.rm = TRUE
      ),
      total_duration_s = sum(
        retained_values,
        na.rm = TRUE
      ) / 1000,
      mean_nni_ms = if (
        length(retained_values) > 0L
      ) {
        mean(retained_values)
      } else {
        NA_real_
      },
      stringsAsFactors = FALSE
    )

    manifest_rows[[group_i]] <- cbind(
      group_values,
      manifest_row
    )
  }

  manifest <- do.call(
    rbind,
    manifest_rows
  )

  rownames(manifest) <- NULL

  files <- .gp_pyhrv_input_write_files(
    vectors = vectors,
    manifest = manifest,
    output_dir = output_dir,
    prefix = prefix,
    write_manifest = write_manifest,
    overwrite = overwrite
  )

  settings <- list(
    ibi_col = ibi_col,
    group_cols = group_cols,
    requested_unit = unit,
    resolved_unit =
      unit_assessment$resolved_unit,
    unit_resolution_method =
      unit_assessment$resolution_method,
    filter = filter,
    min_nni_ms = min_nni_ms,
    max_nni_ms = max_nni_ms,
    collapse_repeated_intervals =
      collapse_repeated_intervals,
    repeated_tolerance_ms =
      repeated_tolerance_ms,
    output_dir = output_dir,
    prefix = prefix,
    write_manifest = write_manifest,
    interpretation_notes = c(
      "Prepared intervals are expressed in milliseconds.",
      "The function prepares data but does not execute Python or pyHRV.",
      "Intervals outside the plausibility range remain visible in the audit table.",
      "Repeated-value collapsing should be enabled only when repeated sample-level interval values represent duplicated export rows.",
      "HRV interpretation requires genuine NN or RR intervals and should not be derived from a vendor summary HRV field."
    )
  )

  structure(
    list(
      intervals = intervals,
      vectors = vectors,
      manifest = manifest,
      files = files,
      settings = settings
    ),
    class = c(
      "gazepoint_pyhrv_input",
      "list"
    )
  )
}

.gp_pyhrv_input_extract <- function(data,
                                    ibi_col,
                                    group_cols) {
  if (
    is.numeric(data) &&
      !is.data.frame(data)
  ) {
    if (length(data) == 0L) {
      stop(
        "`data` must contain at least one interval.",
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

    return(list(
      data = data.frame(
        source_row = seq_along(data),
        .interval_raw = as.numeric(data),
        stringsAsFactors = FALSE
      ),
      ibi_col = NULL,
      group_cols = character()
    ))
  }

  if (!is.data.frame(data)) {
    stop(
      "`data` must be a numeric vector or a data frame.",
      call. = FALSE
    )
  }

  if (nrow(data) == 0L) {
    stop(
      "`data` must contain at least one row.",
      call. = FALSE
    )
  }

  if (is.null(ibi_col)) {
    candidates <- c(
      "IBI_clean_ms",
      "nni_ms",
      "NNI_MS",
      "NNI",
      "RR_ms",
      "RR_MS",
      "RRI_ms",
      "RRI_MS",
      "IBI_MS",
      "IBI",
      "RR",
      "RRI",
      "ibi",
      "rr",
      "rri"
    )

    found <- intersect(
      candidates,
      names(data)
    )

    found <- found[
      vapply(
        data[found],
        is.numeric,
        logical(1)
      )
    ]

    if (length(found) == 0L) {
      stop(
        "Could not identify a numeric IBI, RR, or NNI column. ",
        "Supply `ibi_col` explicitly.",
        call. = FALSE
      )
    }

    ibi_col <- found[1L]
  } else {
    ibi_col <- .gp_pyhrv_input_nonempty_string(
      ibi_col,
      "ibi_col"
    )

    if (!ibi_col %in% names(data)) {
      stop(
        "`ibi_col` was not found in `data`.",
        call. = FALSE
      )
    }

    if (!is.numeric(data[[ibi_col]])) {
      stop(
        "`ibi_col` must identify a numeric column.",
        call. = FALSE
      )
    }
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

  out$.interval_raw <- as.numeric(
    data[[ibi_col]]
  )

  list(
    data = out,
    ibi_col = ibi_col,
    group_cols = group_cols
  )
}

.gp_pyhrv_input_resolve_unit <- function(values,
                                         unit,
                                         column_name) {
  if (!identical(unit, "auto")) {
    return(list(
      resolved_unit = unit,
      resolution_method = "explicit"
    ))
  }

  if (!is.null(column_name)) {
    lower_name <- tolower(column_name)

    if (grepl(
      "(^|_)(ms|msec|millisecond|milliseconds)($|_)",
      lower_name
    )) {
      return(list(
        resolved_unit = "milliseconds",
        resolution_method = "column_name"
      ))
    }

    if (grepl(
      "(^|_)(sec|secs|second|seconds|s)($|_)",
      lower_name
    )) {
      return(list(
        resolved_unit = "seconds",
        resolution_method = "column_name"
      ))
    }
  }

  positive <- values[
    is.finite(values) &
      values > 0
  ]

  if (length(positive) == 0L) {
    stop(
      "Automatic unit assessment requires at least one ",
      "finite positive interval.",
      call. = FALSE
    )
  }

  typical <- stats::median(
    positive,
    na.rm = TRUE
  )

  if (typical <= 10) {
    return(list(
      resolved_unit = "seconds",
      resolution_method = "median_heuristic"
    ))
  }

  if (typical >= 100) {
    return(list(
      resolved_unit = "milliseconds",
      resolution_method = "median_heuristic"
    ))
  }

  stop(
    "Automatic interval-unit assessment was ambiguous. ",
    "Supply `unit = \"seconds\"` or ",
    "`unit = \"milliseconds\"` explicitly.",
    call. = FALSE
  )
}

.gp_pyhrv_input_split_indices <- function(data,
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

.gp_pyhrv_input_write_files <- function(vectors,
                                        manifest,
                                        output_dir,
                                        prefix,
                                        write_manifest,
                                        overwrite) {
  if (is.null(output_dir)) {
    return(data.frame(
      file_type = character(),
      group_id = character(),
      path = character(),
      stringsAsFactors = FALSE
    ))
  }

  output_dir <- .gp_pyhrv_input_nonempty_string(
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

  safe_prefix <- .gp_pyhrv_input_safe_name(
    prefix
  )

  vector_filenames <- character(
    length(vectors)
  )

  used_names <- character()

  for (group_i in seq_along(vectors)) {
    group_id <- names(vectors)[group_i]

    suffix <- if (
      length(vectors) == 1L &&
        identical(group_id, "all")
    ) {
      ""
    } else {
      paste0(
        "_",
        .gp_pyhrv_input_safe_name(group_id)
      )
    }

    filename <- paste0(
      safe_prefix,
      suffix,
      ".csv"
    )

    if (filename %in% used_names) {
      filename <- paste0(
        tools::file_path_sans_ext(
          filename
        ),
        "_",
        group_i,
        ".csv"
      )
    }

    vector_filenames[group_i] <- filename
    used_names <- c(
      used_names,
      filename
    )
  }

  vector_paths <- file.path(
    output_dir,
    vector_filenames
  )

  manifest_path <- if (
    isTRUE(write_manifest)
  ) {
    file.path(
      output_dir,
      paste0(
        safe_prefix,
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

  existing_paths <- candidate_paths[
    file.exists(candidate_paths)
  ]

  if (
    length(existing_paths) > 0L &&
      !isTRUE(overwrite)
  ) {
    stop(
      "Output file already exists: ",
      existing_paths[1L],
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

  for (group_i in seq_along(vectors)) {
    path <- vector_paths[group_i]

    utils::write.table(
      data.frame(
        nni_ms = vectors[[group_i]]
      ),
      file = path,
      sep = ",",
      row.names = FALSE,
      col.names = FALSE,
      quote = FALSE,
      na = ""
    )

    counter <- counter + 1L

    files[[counter]] <- data.frame(
      file_type = "intervals",
      group_id = names(vectors)[group_i],
      path = normalizePath(
        path,
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
      group_id = NA_character_,
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

.gp_pyhrv_input_safe_name <- function(x) {
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

.gp_pyhrv_input_positive_scalar <- function(x,
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

.gp_pyhrv_input_nonnegative_scalar <- function(x,
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

.gp_pyhrv_input_logical_scalar <- function(x,
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

.gp_pyhrv_input_nonempty_string <- function(x,
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
