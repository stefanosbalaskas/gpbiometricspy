#' Assign Gazepoint coordinates to areas of interest
#'
#' Assigns sample-level gaze coordinates or fixation centroids to rectangular
#' or polygonal areas of interest (AOIs). The original rows are preserved and
#' augmented with an AOI label, match count, ambiguity flag, and assignment
#' status.
#'
#' Rectangular AOIs use one row per definition with minimum and maximum x and y
#' coordinates. Polygon AOIs use long-format vertices, with one row per vertex
#' and repeated AOI identifiers or labels.
#'
#' Optional matching columns can restrict AOIs to particular trials, screens,
#' media items, stimuli, or other recording contexts. Missing or blank values
#' in AOI matching columns act as wildcards.
#'
#' @param data A data frame containing gaze coordinates or fixation centroids.
#' @param aois A data frame containing rectangular or polygonal AOI definitions.
#' @param x_col Numeric horizontal-coordinate column in `data`. If `NULL`,
#'   common Gazepoint and fixation-summary names are searched.
#' @param y_col Numeric vertical-coordinate column in `data`. If `NULL`,
#'   common Gazepoint and fixation-summary names are searched.
#' @param aoi_label_col AOI label column in `aois`.
#' @param format AOI-definition format: `"auto"`, `"rectangle"`, or
#'   `"polygon"`.
#' @param aoi_id_col Optional AOI identifier column. For polygon definitions,
#'   this distinguishes multiple polygons with the same label.
#' @param data_match_cols Optional columns in `data` used to restrict eligible
#'   AOI definitions, for example `"trial"` or `"MEDIA_ID"`.
#' @param aoi_match_cols Corresponding columns in `aois`. Must have the same
#'   length and order as `data_match_cols`.
#' @param xmin_col,xmax_col,ymin_col,ymax_col Rectangle-boundary columns.
#' @param vertex_x_col,vertex_y_col Polygon-vertex columns.
#' @param priority_col Optional numeric priority column. Smaller values receive
#'   higher priority when `overlap = "priority"`.
#' @param overlap Rule for coordinates falling within multiple AOIs:
#'   `"priority"`, `"first"`, `"smallest"`, `"all"`, or `"error"`.
#' @param boundary Should coordinates on AOI boundaries be treated as
#'   `"inside"` or `"outside"`?
#' @param output_col Name of the generated AOI-label column.
#' @param match_count_col Name of the generated AOI-match-count column.
#' @param ambiguous_col Name of the generated logical ambiguity column.
#' @param status_col Name of the generated assignment-status column.
#' @param all_separator Separator used when `overlap = "all"`.
#' @param overwrite Logical. If `FALSE`, existing output columns are protected.
#'
#' @return A data frame with class `"gazepoint_aoi_assignment"`. Attributes
#'   `aoi_assignment_log`, `aoi_assignment_settings`, and `aoi_definitions`
#'   contain structured provenance information.
#'
#' @details
#' Supported assignment statuses are:
#'
#' - `"matched"`: exactly one AOI matched;
#' - `"ambiguous_resolved"`: multiple AOIs matched and one was selected;
#' - `"ambiguous_all"`: all matching labels were retained;
#' - `"unmatched"`: valid coordinates did not fall within an eligible AOI;
#' - `"invalid_coordinate"`: x or y was missing or non-finite.
#'
#' Coordinate systems are not transformed. Gaze coordinates and AOI
#' definitions must therefore use the same scale, orientation, and origin.
#'
#' @examples
#' gaze <- data.frame(
#'   gaze_x = c(0.1, 0.5, 0.9),
#'   gaze_y = c(0.5, 0.5, 0.5)
#' )
#'
#' rectangles <- data.frame(
#'   aoi = c("left", "right"),
#'   xmin = c(0, 0.6),
#'   xmax = c(0.4, 1),
#'   ymin = c(0, 0),
#'   ymax = c(1, 1)
#' )
#'
#' assign_gazepoint_aoi(
#'   gaze,
#'   rectangles,
#'   x_col = "gaze_x",
#'   y_col = "gaze_y"
#' )
#'
#' @seealso [summarize_gazepoint_fixations()],
#'   [summarize_gazepoint_aoi_dwell()],
#'   [summarise_gazepoint_aoi_biometrics()]
#'
#' @export
assign_gazepoint_aoi <- function(
    data,
    aois,
    x_col = NULL,
    y_col = NULL,
    aoi_label_col = "aoi",
    format = c("auto", "rectangle", "polygon"),
    aoi_id_col = NULL,
    data_match_cols = NULL,
    aoi_match_cols = data_match_cols,
    xmin_col = "xmin",
    xmax_col = "xmax",
    ymin_col = "ymin",
    ymax_col = "ymax",
    vertex_x_col = "vertex_x",
    vertex_y_col = "vertex_y",
    priority_col = NULL,
    overlap = c(
      "priority",
      "first",
      "smallest",
      "all",
      "error"
    ),
    boundary = c("inside", "outside"),
    output_col = "AOI",
    match_count_col = "aoi_match_count",
    ambiguous_col = "aoi_ambiguous",
    status_col = "aoi_assignment_status",
    all_separator = "|",
    overwrite = FALSE) {
  if (!is.data.frame(data)) {
    stop("`data` must be a data frame.", call. = FALSE)
  }

  if (!is.data.frame(aois)) {
    stop("`aois` must be a data frame.", call. = FALSE)
  }

  if (nrow(data) == 0L) {
    stop("`data` must contain at least one row.", call. = FALSE)
  }

  if (nrow(aois) == 0L) {
    stop("`aois` must contain at least one row.", call. = FALSE)
  }

  format <- match.arg(format)
  overlap <- match.arg(overlap)
  boundary <- match.arg(boundary)

  x_col <- .gp_aoi_assign_resolve_numeric_col(
    data,
    supplied = x_col,
    candidates = c(
      "gaze_x",
      "GAZE_X",
      "BPOGX",
      "FPOGX",
      "GPOGX",
      "LPOGX",
      "RPOGX",
      "mean_x",
      "median_x",
      "fixation_x",
      "fix_x",
      "x",
      "X"
    ),
    argument = "x_col"
  )

  y_col <- .gp_aoi_assign_resolve_numeric_col(
    data,
    supplied = y_col,
    candidates = c(
      "gaze_y",
      "GAZE_Y",
      "BPOGY",
      "FPOGY",
      "GPOGY",
      "LPOGY",
      "RPOGY",
      "mean_y",
      "median_y",
      "fixation_y",
      "fix_y",
      "y",
      "Y"
    ),
    argument = "y_col"
  )

  if (identical(x_col, y_col)) {
    stop(
      "`x_col` and `y_col` must identify different columns.",
      call. = FALSE
    )
  }

  aoi_label_col <- .gp_aoi_assign_scalar_name(
    aoi_label_col,
    "aoi_label_col"
  )

  if (!aoi_label_col %in% names(aois)) {
    stop(
      "`aoi_label_col` was not found in `aois`.",
      call. = FALSE
    )
  }

  if (!is.null(aoi_id_col)) {
    aoi_id_col <- .gp_aoi_assign_scalar_name(
      aoi_id_col,
      "aoi_id_col"
    )

    if (!aoi_id_col %in% names(aois)) {
      stop(
        "`aoi_id_col` was not found in `aois`.",
        call. = FALSE
      )
    }
  }

  if (!is.null(priority_col)) {
    priority_col <- .gp_aoi_assign_scalar_name(
      priority_col,
      "priority_col"
    )

    if (!priority_col %in% names(aois)) {
      stop(
        "`priority_col` was not found in `aois`.",
        call. = FALSE
      )
    }

    if (!is.numeric(aois[[priority_col]])) {
      stop(
        "`priority_col` must identify a numeric column.",
        call. = FALSE
      )
    }
  }

  if (is.null(data_match_cols)) {
    data_match_cols <- character()
  } else {
    data_match_cols <- unique(as.character(data_match_cols))
  }

  if (is.null(aoi_match_cols)) {
    aoi_match_cols <- character()
  } else {
    aoi_match_cols <- as.character(aoi_match_cols)
  }

  if (length(data_match_cols) != length(aoi_match_cols)) {
    stop(
      "`data_match_cols` and `aoi_match_cols` must have equal length.",
      call. = FALSE
    )
  }

  if (
    anyNA(data_match_cols) ||
      any(!nzchar(data_match_cols)) ||
      anyNA(aoi_match_cols) ||
      any(!nzchar(aoi_match_cols))
  ) {
    stop(
      "AOI matching columns must be non-empty names.",
      call. = FALSE
    )
  }

  missing_data_match <- setdiff(data_match_cols, names(data))
  missing_aoi_match <- setdiff(aoi_match_cols, names(aois))

  if (length(missing_data_match) > 0L) {
    stop(
      "`data_match_cols` contains columns not found in `data`: ",
      paste(missing_data_match, collapse = ", "),
      call. = FALSE
    )
  }

  if (length(missing_aoi_match) > 0L) {
    stop(
      "`aoi_match_cols` contains columns not found in `aois`: ",
      paste(missing_aoi_match, collapse = ", "),
      call. = FALSE
    )
  }

  output_cols <- c(
    output_col,
    match_count_col,
    ambiguous_col,
    status_col
  )

  if (
    anyNA(output_cols) ||
      any(!nzchar(output_cols)) ||
      anyDuplicated(output_cols)
  ) {
    stop(
      "Generated output-column names must be distinct and non-empty.",
      call. = FALSE
    )
  }

  protected_input_cols <- c(
    x_col,
    y_col,
    data_match_cols
  )

  if (length(intersect(output_cols, protected_input_cols)) > 0L) {
    stop(
      "Generated columns must not replace coordinate or matching columns.",
      call. = FALSE
    )
  }

  if (
    !is.logical(overwrite) ||
      length(overwrite) != 1L ||
      is.na(overwrite)
  ) {
    stop("`overwrite` must be TRUE or FALSE.", call. = FALSE)
  }

  existing_outputs <- intersect(output_cols, names(data))

  if (!isTRUE(overwrite) && length(existing_outputs) > 0L) {
    stop(
      "Generated columns already exist: ",
      paste(existing_outputs, collapse = ", "),
      ". Use `overwrite = TRUE` to replace them.",
      call. = FALSE
    )
  }

  if (
    !is.character(all_separator) ||
      length(all_separator) != 1L ||
      is.na(all_separator) ||
      !nzchar(all_separator)
  ) {
    stop(
      "`all_separator` must be one non-empty character value.",
      call. = FALSE
    )
  }

  format <- .gp_aoi_assign_resolve_format(
    aois = aois,
    format = format,
    rectangle_cols = c(
      xmin_col,
      xmax_col,
      ymin_col,
      ymax_col
    ),
    polygon_cols = c(
      vertex_x_col,
      vertex_y_col
    )
  )

  definitions <- if (identical(format, "rectangle")) {
    .gp_aoi_assign_prepare_rectangles(
      aois = aois,
      aoi_label_col = aoi_label_col,
      aoi_id_col = aoi_id_col,
      aoi_match_cols = aoi_match_cols,
      data_match_cols = data_match_cols,
      xmin_col = xmin_col,
      xmax_col = xmax_col,
      ymin_col = ymin_col,
      ymax_col = ymax_col,
      priority_col = priority_col
    )
  } else {
    .gp_aoi_assign_prepare_polygons(
      aois = aois,
      aoi_label_col = aoi_label_col,
      aoi_id_col = aoi_id_col,
      aoi_match_cols = aoi_match_cols,
      data_match_cols = data_match_cols,
      vertex_x_col = vertex_x_col,
      vertex_y_col = vertex_y_col,
      priority_col = priority_col
    )
  }

  n_definitions <- length(definitions)
  output_labels <- rep(NA_character_, nrow(data))
  match_counts <- integer(nrow(data))
  ambiguous <- rep(FALSE, nrow(data))
  status <- rep("unmatched", nrow(data))

  candidate_hits <- integer(n_definitions)
  selected_hits <- integer(n_definitions)

  gaze_x <- data[[x_col]]
  gaze_y <- data[[y_col]]

  valid_coordinate <- is.finite(gaze_x) & is.finite(gaze_y)
  status[!valid_coordinate] <- "invalid_coordinate"

  for (row_i in which(valid_coordinate)) {
    eligible <- vapply(
      definitions,
      .gp_aoi_assign_metadata_matches,
      logical(1),
      data = data,
      row_i = row_i
    )

    if (!any(eligible)) {
      next
    }

    eligible_ids <- which(eligible)

    inside <- vapply(
      definitions[eligible_ids],
      .gp_aoi_assign_contains_point,
      logical(1),
      x = gaze_x[row_i],
      y = gaze_y[row_i],
      boundary = boundary
    )

    matched_ids <- eligible_ids[inside]

    if (length(matched_ids) == 0L) {
      next
    }

    candidate_hits[matched_ids] <-
      candidate_hits[matched_ids] + 1L

    match_counts[row_i] <- length(matched_ids)

    if (length(matched_ids) == 1L) {
      selected_id <- matched_ids
      output_labels[row_i] <- definitions[[selected_id]]$label
      selected_hits[selected_id] <- selected_hits[selected_id] + 1L
      status[row_i] <- "matched"
      next
    }

    ambiguous[row_i] <- TRUE

    if (identical(overlap, "error")) {
      labels <- vapply(
        definitions[matched_ids],
        function(definition) definition$label,
        character(1)
      )

      stop(
        "Multiple AOIs matched data row ",
        row_i,
        ": ",
        paste(labels, collapse = ", "),
        ".",
        call. = FALSE
      )
    }

    if (identical(overlap, "all")) {
      ordered_ids <- matched_ids[
        order(vapply(
          definitions[matched_ids],
          function(definition) definition$order,
          numeric(1)
        ))
      ]

      labels <- unique(vapply(
        definitions[ordered_ids],
        function(definition) definition$label,
        character(1)
      ))

      output_labels[row_i] <- paste(
        labels,
        collapse = all_separator
      )

      selected_hits[ordered_ids] <-
        selected_hits[ordered_ids] + 1L

      status[row_i] <- "ambiguous_all"
      next
    }

    selected_id <- .gp_aoi_assign_resolve_overlap(
      definitions = definitions,
      matched_ids = matched_ids,
      overlap = overlap
    )

    output_labels[row_i] <- definitions[[selected_id]]$label
    selected_hits[selected_id] <- selected_hits[selected_id] + 1L
    status[row_i] <- "ambiguous_resolved"
  }

  out <- data
  out[[output_col]] <- output_labels
  out[[match_count_col]] <- match_counts
  out[[ambiguous_col]] <- ambiguous
  out[[status_col]] <- status

  definition_table <- .gp_aoi_assign_definition_table(
    definitions,
    candidate_hits = candidate_hits,
    selected_hits = selected_hits
  )

  valid_rows <- sum(valid_coordinate)
  assigned_rows <- sum(!is.na(output_labels))

  overview <- data.frame(
    n_rows = nrow(data),
    n_valid_coordinates = valid_rows,
    n_invalid_coordinates = sum(!valid_coordinate),
    n_assigned = assigned_rows,
    n_unmatched = sum(status == "unmatched"),
    n_ambiguous = sum(ambiguous),
    assignment_rate_valid = if (valid_rows > 0L) {
      assigned_rows / valid_rows
    } else {
      NA_real_
    },
    aoi_definition_count = n_definitions,
    aoi_format = format,
    overlap_rule = overlap,
    boundary_rule = boundary,
    stringsAsFactors = FALSE
  )

  settings <- list(
    x_col = x_col,
    y_col = y_col,
    aoi_label_col = aoi_label_col,
    format = format,
    aoi_id_col = aoi_id_col,
    data_match_cols = data_match_cols,
    aoi_match_cols = aoi_match_cols,
    rectangle_cols = c(
      xmin = xmin_col,
      xmax = xmax_col,
      ymin = ymin_col,
      ymax = ymax_col
    ),
    polygon_cols = c(
      vertex_x = vertex_x_col,
      vertex_y = vertex_y_col
    ),
    priority_col = priority_col,
    overlap = overlap,
    boundary = boundary,
    output_col = output_col,
    match_count_col = match_count_col,
    ambiguous_col = ambiguous_col,
    status_col = status_col,
    all_separator = all_separator,
    interpretation_notes = c(
      "Coordinates and AOI definitions must use the same coordinate system.",
      "AOI assignment identifies geometric membership and does not establish attention, comprehension, or cognitive processing.",
      "Overlapping AOIs should be resolved using a prespecified and reported rule."
    )
  )

  attr(out, "aoi_assignment_log") <- list(
    overview = overview,
    definitions = definition_table
  )

  attr(out, "aoi_assignment_settings") <- settings
  attr(out, "aoi_definitions") <- aois

  class(out) <- unique(c(
    "gazepoint_aoi_assignment",
    class(out)
  ))

  out
}

.gp_aoi_assign_resolve_numeric_col <- function(data,
                                                supplied,
                                                candidates,
                                                argument) {
  if (!is.null(supplied)) {
    supplied <- .gp_aoi_assign_scalar_name(
      supplied,
      argument
    )

    if (!supplied %in% names(data)) {
      stop(
        "Column `",
        supplied,
        "` supplied through `",
        argument,
        "` was not found.",
        call. = FALSE
      )
    }

    if (!is.numeric(data[[supplied]])) {
      stop(
        "`",
        argument,
        "` must identify a numeric column.",
        call. = FALSE
      )
    }

    return(supplied)
  }

  found <- intersect(candidates, names(data))

  found <- found[
    vapply(data[found], is.numeric, logical(1))
  ]

  if (length(found) == 0L) {
    stop(
      "Could not identify a numeric `",
      argument,
      "` column. Supply it explicitly.",
      call. = FALSE
    )
  }

  found[1L]
}

.gp_aoi_assign_scalar_name <- function(x,
                                       argument) {
  x <- as.character(x)

  if (
    length(x) != 1L ||
      is.na(x) ||
      !nzchar(x)
  ) {
    stop(
      "`",
      argument,
      "` must be one non-empty column name.",
      call. = FALSE
    )
  }

  x
}

.gp_aoi_assign_resolve_format <- function(aois,
                                          format,
                                          rectangle_cols,
                                          polygon_cols) {
  if (!identical(format, "auto")) {
    required <- if (identical(format, "rectangle")) {
      rectangle_cols
    } else {
      polygon_cols
    }

    missing <- setdiff(required, names(aois))

    if (length(missing) > 0L) {
      stop(
        "Required ",
        format,
        " AOI columns were not found: ",
        paste(missing, collapse = ", "),
        call. = FALSE
      )
    }

    return(format)
  }

  has_rectangle <- all(rectangle_cols %in% names(aois))
  has_polygon <- all(polygon_cols %in% names(aois))

  rectangle_complete <- FALSE
  polygon_complete <- FALSE

  if (has_rectangle) {
    rectangle_complete <- any(stats::complete.cases(
      aois[rectangle_cols]
    ))
  }

  if (has_polygon) {
    polygon_complete <- any(stats::complete.cases(
      aois[polygon_cols]
    ))
  }

  if (rectangle_complete && polygon_complete) {
    stop(
      "Both rectangle and polygon columns contain definitions. ",
      "Set `format` explicitly.",
      call. = FALSE
    )
  }

  if (rectangle_complete) {
    return("rectangle")
  }

  if (polygon_complete) {
    return("polygon")
  }

  stop(
    "Could not infer AOI format. Supply complete rectangle or polygon columns.",
    call. = FALSE
  )
}

.gp_aoi_assign_prepare_rectangles <- function(
    aois,
    aoi_label_col,
    aoi_id_col,
    aoi_match_cols,
    data_match_cols,
    xmin_col,
    xmax_col,
    ymin_col,
    ymax_col,
    priority_col) {
  boundary_cols <- c(
    xmin_col,
    xmax_col,
    ymin_col,
    ymax_col
  )

  missing <- setdiff(boundary_cols, names(aois))

  if (length(missing) > 0L) {
    stop(
      "Rectangle columns were not found: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- boundary_cols[
    !vapply(aois[boundary_cols], is.numeric, logical(1))
  ]

  if (length(non_numeric) > 0L) {
    stop(
      "Rectangle boundary columns must be numeric: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  definitions <- vector("list", nrow(aois))

  for (i in seq_len(nrow(aois))) {
    label <- trimws(as.character(aois[[aoi_label_col]][i]))

    if (is.na(label) || !nzchar(label)) {
      stop(
        "AOI row ",
        i,
        " has a missing or blank label.",
        call. = FALSE
      )
    }

    bounds <- as.numeric(aois[i, boundary_cols])

    if (any(!is.finite(bounds))) {
      stop(
        "AOI row ",
        i,
        " has non-finite rectangle boundaries.",
        call. = FALSE
      )
    }

    xmin <- aois[[xmin_col]][i]
    xmax <- aois[[xmax_col]][i]
    ymin <- aois[[ymin_col]][i]
    ymax <- aois[[ymax_col]][i]

    if (xmin >= xmax || ymin >= ymax) {
      stop(
        "AOI row ",
        i,
        " must satisfy xmin < xmax and ymin < ymax.",
        call. = FALSE
      )
    }

    priority <- if (is.null(priority_col)) {
      i
    } else {
      aois[[priority_col]][i]
    }

    if (!is.finite(priority)) {
      stop(
        "AOI row ",
        i,
        " has a non-finite priority.",
        call. = FALSE
      )
    }

    aoi_id <- if (is.null(aoi_id_col)) {
      paste0("rectangle_", i)
    } else {
      as.character(aois[[aoi_id_col]][i])
    }

    if (is.na(aoi_id) || !nzchar(trimws(aoi_id))) {
      stop(
        "AOI row ",
        i,
        " has a missing or blank identifier.",
        call. = FALSE
      )
    }

    definitions[[i]] <- list(
      id = aoi_id,
      label = label,
      shape = "rectangle",
      order = i,
      priority = priority,
      area = (xmax - xmin) * (ymax - ymin),
      xmin = xmin,
      xmax = xmax,
      ymin = ymin,
      ymax = ymax,
      match_values = .gp_aoi_assign_match_values(
        aois = aois,
        rows = i,
        aoi_match_cols = aoi_match_cols,
        data_match_cols = data_match_cols,
        definition_id = aoi_id
      )
    )
  }

  definitions
}

.gp_aoi_assign_prepare_polygons <- function(
    aois,
    aoi_label_col,
    aoi_id_col,
    aoi_match_cols,
    data_match_cols,
    vertex_x_col,
    vertex_y_col,
    priority_col) {
  vertex_cols <- c(vertex_x_col, vertex_y_col)
  missing <- setdiff(vertex_cols, names(aois))

  if (length(missing) > 0L) {
    stop(
      "Polygon vertex columns were not found: ",
      paste(missing, collapse = ", "),
      call. = FALSE
    )
  }

  non_numeric <- vertex_cols[
    !vapply(aois[vertex_cols], is.numeric, logical(1))
  ]

  if (length(non_numeric) > 0L) {
    stop(
      "Polygon vertex columns must be numeric: ",
      paste(non_numeric, collapse = ", "),
      call. = FALSE
    )
  }

  grouping_cols <- unique(c(
    if (is.null(aoi_id_col)) {
      aoi_label_col
    } else {
      aoi_id_col
    },
    aoi_match_cols
  ))

  groups <- .gp_aoi_assign_split_rows(
    aois,
    grouping_cols
  )

  definitions <- vector("list", length(groups))

  for (group_i in seq_along(groups)) {
    rows <- groups[[group_i]]

    labels <- unique(trimws(
      as.character(aois[[aoi_label_col]][rows])
    ))

    labels <- labels[
      !is.na(labels) & nzchar(labels)
    ]

    if (length(labels) != 1L) {
      stop(
        "Polygon group ",
        group_i,
        " must contain exactly one non-empty AOI label.",
        call. = FALSE
      )
    }

    aoi_id <- if (is.null(aoi_id_col)) {
      labels
    } else {
      ids <- unique(trimws(
        as.character(aois[[aoi_id_col]][rows])
      ))

      ids <- ids[!is.na(ids) & nzchar(ids)]

      if (length(ids) != 1L) {
        stop(
          "Polygon group ",
          group_i,
          " must contain exactly one non-empty AOI identifier.",
          call. = FALSE
        )
      }

      ids
    }

    vertex_x <- aois[[vertex_x_col]][rows]
    vertex_y <- aois[[vertex_y_col]][rows]

    if (
      any(!is.finite(vertex_x)) ||
        any(!is.finite(vertex_y))
    ) {
      stop(
        "Polygon `",
        aoi_id,
        "` contains non-finite vertices.",
        call. = FALSE
      )
    }

    unique_vertices <- unique(data.frame(
      x = vertex_x,
      y = vertex_y
    ))

    if (nrow(unique_vertices) < 3L) {
      stop(
        "Polygon `",
        aoi_id,
        "` requires at least three unique vertices.",
        call. = FALSE
      )
    }

    area <- .gp_aoi_assign_polygon_area(
      vertex_x,
      vertex_y
    )

    if (!is.finite(area) || area <= 0) {
      stop(
        "Polygon `",
        aoi_id,
        "` has zero or invalid area.",
        call. = FALSE
      )
    }

    priority <- if (is.null(priority_col)) {
      group_i
    } else {
      priorities <- unique(aois[[priority_col]][rows])

      if (
        length(priorities) != 1L ||
          !is.finite(priorities)
      ) {
        stop(
          "Polygon `",
          aoi_id,
          "` must have one finite priority.",
          call. = FALSE
        )
      }

      priorities
    }

    definitions[[group_i]] <- list(
      id = aoi_id,
      label = labels,
      shape = "polygon",
      order = group_i,
      priority = priority,
      area = area,
      vertex_x = vertex_x,
      vertex_y = vertex_y,
      match_values = .gp_aoi_assign_match_values(
        aois = aois,
        rows = rows,
        aoi_match_cols = aoi_match_cols,
        data_match_cols = data_match_cols,
        definition_id = aoi_id
      )
    )
  }

  definitions
}

.gp_aoi_assign_split_rows <- function(data,
                                      group_cols) {
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
    c(grouping, sep = "\u001f")
  )

  split(
    seq_len(nrow(data)),
    factor(key, levels = unique(key)),
    drop = TRUE
  )
}

.gp_aoi_assign_match_values <- function(
    aois,
    rows,
    aoi_match_cols,
    data_match_cols,
    definition_id) {
  if (length(aoi_match_cols) == 0L) {
    return(list())
  }

  values <- vector("list", length(aoi_match_cols))
  names(values) <- data_match_cols

  for (i in seq_along(aoi_match_cols)) {
    column <- aoi_match_cols[i]
    raw_values <- aois[[column]][rows]
    normalized <- as.character(raw_values)
    normalized[is.na(normalized)] <- "<NA>"

    if (length(unique(normalized)) != 1L) {
      stop(
        "AOI definition `",
        definition_id,
        "` contains inconsistent values in `",
        column,
        "`.",
        call. = FALSE
      )
    }

    values[[i]] <- raw_values[1L]
  }

  values
}

.gp_aoi_assign_metadata_matches <- function(definition,
                                            data,
                                            row_i) {
  if (length(definition$match_values) == 0L) {
    return(TRUE)
  }

  for (column in names(definition$match_values)) {
    required_value <- definition$match_values[[column]]
    required_text <- as.character(required_value)

    wildcard <- is.na(required_value) ||
      is.na(required_text) ||
      !nzchar(trimws(required_text))

    if (wildcard) {
      next
    }

    observed_value <- data[[column]][row_i]

    if (is.na(observed_value)) {
      return(FALSE)
    }

    if (!identical(
      as.character(observed_value),
      required_text
    )) {
      return(FALSE)
    }
  }

  TRUE
}

.gp_aoi_assign_contains_point <- function(definition,
                                          x,
                                          y,
                                          boundary) {
  if (identical(definition$shape, "rectangle")) {
    tolerance <- sqrt(.Machine$double.eps) *
      max(
        1,
        abs(c(
          x,
          y,
          definition$xmin,
          definition$xmax,
          definition$ymin,
          definition$ymax
        ))
      )

    if (identical(boundary, "inside")) {
      return(
        x >= definition$xmin - tolerance &&
          x <= definition$xmax + tolerance &&
          y >= definition$ymin - tolerance &&
          y <= definition$ymax + tolerance
      )
    }

    return(
      x > definition$xmin + tolerance &&
        x < definition$xmax - tolerance &&
        y > definition$ymin + tolerance &&
        y < definition$ymax - tolerance
    )
  }

  .gp_aoi_assign_point_in_polygon(
    x = x,
    y = y,
    vertex_x = definition$vertex_x,
    vertex_y = definition$vertex_y,
    boundary = boundary
  )
}

.gp_aoi_assign_point_in_polygon <- function(
    x,
    y,
    vertex_x,
    vertex_y,
    boundary) {
  n_vertices <- length(vertex_x)

  tolerance <- sqrt(.Machine$double.eps) *
    max(
      1,
      abs(c(x, y, vertex_x, vertex_y))
    )

  previous <- c(n_vertices, seq_len(n_vertices - 1L))

  on_boundary <- vapply(
    seq_len(n_vertices),
    function(i) {
      .gp_aoi_assign_point_on_segment(
        x = x,
        y = y,
        x1 = vertex_x[previous[i]],
        y1 = vertex_y[previous[i]],
        x2 = vertex_x[i],
        y2 = vertex_y[i],
        tolerance = tolerance
      )
    },
    logical(1)
  )

  if (any(on_boundary)) {
    return(identical(boundary, "inside"))
  }

  inside <- FALSE
  j <- n_vertices

  for (i in seq_len(n_vertices)) {
    crosses_y <- (vertex_y[i] > y) !=
      (vertex_y[j] > y)

    if (crosses_y) {
      crossing_x <- (
        (vertex_x[j] - vertex_x[i]) *
          (y - vertex_y[i]) /
          (vertex_y[j] - vertex_y[i])
      ) + vertex_x[i]

      if (x < crossing_x) {
        inside <- !inside
      }
    }

    j <- i
  }

  inside
}

.gp_aoi_assign_point_on_segment <- function(
    x,
    y,
    x1,
    y1,
    x2,
    y2,
    tolerance) {
  cross_product <- (x - x1) * (y2 - y1) -
    (y - y1) * (x2 - x1)

  scale <- max(
    1,
    abs(c(x1, y1, x2, y2))
  )

  if (abs(cross_product) > tolerance * scale) {
    return(FALSE)
  }

  within_x <- x >= min(x1, x2) - tolerance &&
    x <= max(x1, x2) + tolerance

  within_y <- y >= min(y1, y2) - tolerance &&
    y <= max(y1, y2) + tolerance

  within_x && within_y
}

.gp_aoi_assign_polygon_area <- function(vertex_x,
                                        vertex_y) {
  next_vertex <- c(
    seq.int(2L, length(vertex_x)),
    1L
  )

  abs(sum(
    vertex_x * vertex_y[next_vertex] -
      vertex_x[next_vertex] * vertex_y
  )) / 2
}

.gp_aoi_assign_resolve_overlap <- function(
    definitions,
    matched_ids,
    overlap) {
  priority <- vapply(
    definitions[matched_ids],
    function(definition) definition$priority,
    numeric(1)
  )

  definition_order <- vapply(
    definitions[matched_ids],
    function(definition) definition$order,
    numeric(1)
  )

  area <- vapply(
    definitions[matched_ids],
    function(definition) definition$area,
    numeric(1)
  )

  ordering <- switch(
    overlap,
    priority = order(
      priority,
      definition_order
    ),
    first = order(
      definition_order
    ),
    smallest = order(
      area,
      priority,
      definition_order
    )
  )

  matched_ids[ordering[1L]]
}

.gp_aoi_assign_definition_table <- function(
    definitions,
    candidate_hits,
    selected_hits) {
  rows <- lapply(
    seq_along(definitions),
    function(i) {
      definition <- definitions[[i]]

      row <- data.frame(
        aoi_id = definition$id,
        aoi_label = definition$label,
        shape = definition$shape,
        definition_order = definition$order,
        priority = definition$priority,
        area = definition$area,
        candidate_hits = candidate_hits[i],
        selected_hits = selected_hits[i],
        stringsAsFactors = FALSE
      )

      if (length(definition$match_values) > 0L) {
        match_values <- as.data.frame(
          definition$match_values,
          stringsAsFactors = FALSE,
          optional = TRUE
        )

        row <- cbind(row, match_values)
      }

      row
    }
  )

  out <- do.call(rbind, rows)
  rownames(out) <- NULL
  out
}
