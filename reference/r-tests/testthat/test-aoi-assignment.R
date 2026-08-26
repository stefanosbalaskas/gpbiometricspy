test_that("assign_gazepoint_aoi assigns rectangular AOIs", {
  gaze <- data.frame(
    gaze_x = c(0.1, 0.5, 0.9, NA),
    gaze_y = c(0.5, 0.5, 0.5, 0.5)
  )

  aois <- data.frame(
    aoi = c("left", "right"),
    xmin = c(0, 0.6),
    xmax = c(0.4, 1),
    ymin = c(0, 0),
    ymax = c(1, 1)
  )

  out <- assign_gazepoint_aoi(
    gaze,
    aois,
    x_col = "gaze_x",
    y_col = "gaze_y"
  )

  expect_s3_class(out, "gazepoint_aoi_assignment")
  expect_equal(
    out$AOI,
    c("left", NA, "right", NA)
  )
  expect_equal(out$aoi_match_count, c(1L, 0L, 1L, 0L))
  expect_equal(
    out$aoi_assignment_status,
    c(
      "matched",
      "unmatched",
      "matched",
      "invalid_coordinate"
    )
  )
  expect_false(any(out$aoi_ambiguous))

  log <- attr(out, "aoi_assignment_log")
  expect_true(is.list(log))
  expect_equal(log$overview$n_assigned, 2)
  expect_equal(log$overview$n_invalid_coordinates, 1)
})

test_that("rectangle boundary handling is explicit", {
  gaze <- data.frame(
    gaze_x = 0.4,
    gaze_y = 0.5
  )

  aois <- data.frame(
    aoi = "left",
    xmin = 0,
    xmax = 0.4,
    ymin = 0,
    ymax = 1
  )

  inside <- assign_gazepoint_aoi(
    gaze,
    aois,
    boundary = "inside"
  )

  outside <- assign_gazepoint_aoi(
    gaze,
    aois,
    boundary = "outside"
  )

  expect_equal(inside$AOI, "left")
  expect_true(is.na(outside$AOI))
})

test_that("assign_gazepoint_aoi handles overlap rules", {
  gaze <- data.frame(
    gaze_x = 0.5,
    gaze_y = 0.5
  )

  aois <- data.frame(
    aoi = c("large", "small"),
    xmin = c(0, 0.25),
    xmax = c(1, 0.75),
    ymin = c(0, 0.25),
    ymax = c(1, 0.75),
    priority = c(2, 1)
  )

  priority <- assign_gazepoint_aoi(
    gaze,
    aois,
    priority_col = "priority",
    overlap = "priority"
  )

  first <- assign_gazepoint_aoi(
    gaze,
    aois,
    priority_col = "priority",
    overlap = "first"
  )

  smallest <- assign_gazepoint_aoi(
    gaze,
    aois,
    priority_col = "priority",
    overlap = "smallest"
  )

  all <- assign_gazepoint_aoi(
    gaze,
    aois,
    priority_col = "priority",
    overlap = "all"
  )

  expect_equal(priority$AOI, "small")
  expect_equal(first$AOI, "large")
  expect_equal(smallest$AOI, "small")
  expect_equal(all$AOI, "large|small")

  expect_true(priority$aoi_ambiguous)
  expect_equal(priority$aoi_match_count, 2L)
  expect_equal(
    priority$aoi_assignment_status,
    "ambiguous_resolved"
  )
  expect_equal(
    all$aoi_assignment_status,
    "ambiguous_all"
  )

  expect_error(
    assign_gazepoint_aoi(
      gaze,
      aois,
      overlap = "error"
    ),
    "Multiple AOIs"
  )
})

test_that("assign_gazepoint_aoi supports polygon definitions", {
  gaze <- data.frame(
    mean_x = c(0.5, 1.5, 0),
    mean_y = c(0.5, 0.5, 0.5)
  )

  polygon <- data.frame(
    aoi_id = "square_1",
    aoi = "square",
    vertex_x = c(0, 1, 1, 0),
    vertex_y = c(0, 0, 1, 1)
  )

  inside <- assign_gazepoint_aoi(
    gaze,
    polygon,
    format = "polygon",
    aoi_id_col = "aoi_id",
    boundary = "inside"
  )

  outside <- assign_gazepoint_aoi(
    gaze,
    polygon,
    format = "polygon",
    aoi_id_col = "aoi_id",
    boundary = "outside"
  )

  expect_equal(
    inside$AOI,
    c("square", NA, "square")
  )

  expect_equal(
    outside$AOI,
    c("square", NA, NA)
  )

  definitions <- attr(
    inside,
    "aoi_assignment_log"
  )$definitions

  expect_equal(definitions$shape, "polygon")
  expect_equal(definitions$area, 1)
})

test_that("AOI definitions can be restricted by recording context", {
  gaze <- data.frame(
    screen = c("A", "B", "C"),
    gaze_x = c(0.25, 0.25, 0.25),
    gaze_y = c(0.5, 0.5, 0.5)
  )

  aois <- data.frame(
    screen_name = c("A", "B", NA),
    aoi = c("screen_A", "screen_B", "global"),
    xmin = 0,
    xmax = 0.5,
    ymin = 0,
    ymax = 1,
    priority = c(1, 1, 5)
  )

  out <- assign_gazepoint_aoi(
    gaze,
    aois,
    data_match_cols = "screen",
    aoi_match_cols = "screen_name",
    priority_col = "priority",
    overlap = "priority"
  )

  expect_equal(
    out$AOI,
    c("screen_A", "screen_B", "global")
  )

  expect_equal(
    out$aoi_match_count,
    c(2L, 2L, 1L)
  )

  expect_equal(
    out$aoi_ambiguous,
    c(TRUE, TRUE, FALSE)
  )
})

test_that("polygon definitions require valid vertices", {
  gaze <- data.frame(
    gaze_x = 0.5,
    gaze_y = 0.5
  )

  malformed <- data.frame(
    aoi = "triangle",
    vertex_x = c(0, 1),
    vertex_y = c(0, 0)
  )

  expect_error(
    assign_gazepoint_aoi(
      gaze,
      malformed,
      format = "polygon"
    ),
    "at least three"
  )
})

test_that("assign_gazepoint_aoi validates inputs", {
  gaze <- data.frame(
    gaze_x = 0.5,
    gaze_y = 0.5,
    label = "x"
  )

  aois <- data.frame(
    aoi = "center",
    xmin = 0,
    xmax = 1,
    ymin = 0,
    ymax = 1
  )

  expect_error(
    assign_gazepoint_aoi(
      gaze,
      aois,
      x_col = "label",
      y_col = "gaze_y"
    ),
    "numeric"
  )

  expect_error(
    assign_gazepoint_aoi(
      gaze,
      transform(aois, xmax = 0),
      x_col = "gaze_x",
      y_col = "gaze_y"
    ),
    "xmin < xmax"
  )

  expect_error(
    assign_gazepoint_aoi(
      gaze,
      aois,
      data_match_cols = "missing",
      aoi_match_cols = "screen"
    ),
    "not found"
  )

  expect_error(
    assign_gazepoint_aoi(
      transform(gaze, AOI = "old"),
      aois
    ),
    "already exist"
  )
})
