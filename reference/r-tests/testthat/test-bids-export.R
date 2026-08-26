test_that("BIDS export dry run creates a standards-oriented manifest", {
  skip_if_not_installed("jsonlite")

  root <- tempfile("bids-preview-")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2, 0.3),
    BPOGX = c(0.4, 0.5, 0.6, 0.5),
    BPOGY = c(0.5, 0.4, 0.5, 0.6)
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = root,
    subject = "01",
    task = "viewing",
    dataset_name = "Viewing study",
    recorded_eye = "cyclopean",
    coordinate_units = "normalized",
    screen_distance_m = 0.6,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1920, 1080),
    screen_size_m = c(0.53, 0.30),
    dry_run = TRUE
  )

  expect_s3_class(
    out,
    "gazepoint_bids_export"
  )

  expect_false(dir.exists(root))
  expect_true(out$audit$ready_to_write)

  expect_equal(
    names(out$data),
    c(
      "timestamp",
      "x_coordinate",
      "y_coordinate"
    )
  )

  expect_true(any(grepl(
    "sub-01_task-viewing_recording-eye1_physio.tsv.gz$",
    out$files$path
  )))

  expect_true(any(grepl(
    "sub-01_task-viewing_events.json$",
    out$files$path
  )))
})

test_that("BIDS export writes compressed headerless data and JSON", {
  skip_if_not_installed("jsonlite")

  root <- tempfile("bids-write-")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2, 0.3),
    BPOGX = c(0.4, 0.5, NA, 0.5),
    BPOGY = c(0.5, 0.4, 0.5, 0.6),
    PUPIL = c(3.0, 3.1, 3.2, 3.1)
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = root,
    subject = "01",
    task = "viewing",
    dataset_name = "Viewing study",
    recorded_eye = "cyclopean",
    coordinate_units = "normalized",
    pupil_units = "mm",
    screen_distance_m = 0.6,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1920, 1080),
    screen_size_m = c(0.53, 0.30)
  )

  expect_true(all(file.exists(out$files$path)))

  data_path <- out$files$path[
    out$files$role == "physio_tsv_gz"
  ]

  connection <- gzfile(data_path, open = "rt")
  lines <- readLines(connection, warn = FALSE)
  close(connection)

  expect_length(lines, 4)
  expect_equal(
    strsplit(lines[1], "\t", fixed = TRUE)[[1]],
    c("0", "0.4", "0.5", "3")
  )
  expect_match(lines[3], "n/a")

  json_path <- out$files$path[
    out$files$role == "physio_json"
  ]

  sidecar <- jsonlite::read_json(
    json_path,
    simplifyVector = TRUE
  )

  expect_equal(
    sidecar$Columns,
    c(
      "timestamp",
      "x_coordinate",
      "y_coordinate",
      "pupil_size"
    )
  )

  expect_equal(sidecar$PhysioType, "eyetrack")
  expect_equal(sidecar$RecordedEye, "cyclopean")
  expect_equal(sidecar$SampleCoordinateSystem, "gaze-on-screen")
  expect_equal(sidecar$x_coordinate$Units, "1")
  expect_equal(sidecar$y_coordinate$Units, "1")
  expect_equal(sidecar$pupil_size$Units, "mm")

  unlink(root, recursive = TRUE, force = TRUE)
})

test_that("Gazepoint left-eye columns are detected", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    TIME = c(0, 0.01, 0.02),
    LPOGX = c(0.3, 0.4, 0.5),
    LPOGY = c(0.6, 0.5, 0.4),
    LPD = c(3.1, 3.2, 3.3)
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = tempfile("bids-left-"),
    subject = "02",
    task = "search",
    dataset_name = "Search study",
    recorded_eye = "left",
    recording = "eye1",
    coordinate_units = "normalized",
    screen_distance_m = 0.65,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1280, 720),
    screen_size_m = c(0.44, 0.25),
    dry_run = TRUE
  )

  expect_equal(out$settings$x_col, "LPOGX")
  expect_equal(out$settings$y_col, "LPOGY")
  expect_equal(out$settings$pupil_col, "LPD")
  expect_equal(out$audit$sampling_rate_hz, 100)
})

test_that("millisecond timestamps are preserved and interpreted correctly", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    TIMETICK = c(1000, 1010, 1020, 1030),
    RPOGX = c(100, 101, 102, 103),
    RPOGY = c(200, 201, 202, 203)
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = tempfile("bids-ms-"),
    subject = "03",
    task = "reading",
    dataset_name = "Reading study",
    recorded_eye = "right",
    coordinate_units = "pixel",
    screen_distance_m = 0.60,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1920, 1080),
    screen_size_m = c(0.53, 0.30),
    dry_run = TRUE
  )

  expect_equal(
    out$data$timestamp,
    c(1000, 1010, 1020, 1030)
  )

  expect_equal(
    out$physio_sidecar$timestamp$Units,
    "ms"
  )

  expect_equal(
    out$audit$sampling_rate_hz,
    100
  )
})

test_that("additional numeric and logical columns follow prescribed columns", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2),
    BPOGX = c(0.4, 0.5, 0.6),
    BPOGY = c(0.5, 0.6, 0.7),
    BPOGV = c(TRUE, FALSE, TRUE),
    fixation_id = c(1, 1, 2)
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = tempfile("bids-extra-"),
    subject = "04",
    task = "viewing",
    dataset_name = "Additional columns",
    recorded_eye = "cyclopean",
    coordinate_units = "normalized",
    additional_cols = c("BPOGV", "fixation_id"),
    column_metadata = list(
      BPOGV = list(
        Description = "Gazepoint best-point validity flag."
      )
    ),
    screen_distance_m = 0.6,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1920, 1080),
    screen_size_m = c(0.53, 0.30),
    dry_run = TRUE
  )

  expect_equal(
    names(out$data),
    c(
      "timestamp",
      "x_coordinate",
      "y_coordinate",
      "BPOGV",
      "fixation_id"
    )
  )

  expect_equal(out$data$BPOGV, c(1, 0, 1))
  expect_match(
    out$physio_sidecar$BPOGV$Description,
    "validity"
  )
})

test_that("gaze-on-screen export requires complete screen metadata", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2),
    BPOGX = c(0.4, 0.5, 0.6),
    BPOGY = c(0.5, 0.6, 0.7)
  )

  expect_error(
    export_gazepoint_to_bids(
      gaze,
      bids_root = tempfile("bids-screen-"),
      subject = "05",
      task = "viewing",
      dataset_name = "Missing screen metadata",
      recorded_eye = "cyclopean",
      coordinate_units = "normalized",
      dry_run = TRUE
    ),
    "requires events metadata"
  )
})

test_that("non-screen coordinate systems do not require events metadata", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    timestamp = c(0, 0.01, 0.02),
    x_coordinate = c(1, 2, 3),
    y_coordinate = c(4, 5, 6)
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = tempfile("bids-head-"),
    subject = "06",
    task = "tracking",
    dataset_name = "Eye-in-head study",
    recorded_eye = "right",
    sample_coordinate_system = "eye-in-head",
    coordinate_units = "degree",
    dry_run = TRUE
  )

  expect_false(
    "events_json" %in% out$files$role
  )

  expect_equal(
    out$physio_sidecar$x_coordinate$Units,
    "deg"
  )
})

test_that("irregular and non-increasing timestamps are rejected", {
  skip_if_not_installed("jsonlite")

  irregular <- data.frame(
    TIME = c(0, 0.1, 0.2, 0.5),
    BPOGX = 1:4,
    BPOGY = 5:8
  )

  expect_error(
    export_gazepoint_to_bids(
      irregular,
      bids_root = tempfile("bids-irregular-"),
      subject = "07",
      task = "viewing",
      dataset_name = "Irregular",
      recorded_eye = "cyclopean",
      sample_coordinate_system = "eye-in-head",
      coordinate_units = "degree",
      dry_run = TRUE
    ),
    "not regularly sampled"
  )

  reversed <- irregular
  reversed$TIME <- c(0, 0.1, 0.05, 0.2)

  expect_error(
    export_gazepoint_to_bids(
      reversed,
      bids_root = tempfile("bids-reverse-"),
      subject = "07",
      task = "viewing",
      dataset_name = "Reversed",
      recorded_eye = "cyclopean",
      sample_coordinate_system = "eye-in-head",
      coordinate_units = "degree",
      dry_run = TRUE
    ),
    "strictly increasing"
  )
})

test_that("existing recording outputs are protected", {
  skip_if_not_installed("jsonlite")

  root <- tempfile("bids-protect-")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2),
    BPOGX = c(0.4, 0.5, 0.6),
    BPOGY = c(0.5, 0.6, 0.7)
  )

  first <- export_gazepoint_to_bids(
    gaze,
    bids_root = root,
    subject = "08",
    task = "viewing",
    dataset_name = "Protected study",
    recorded_eye = "cyclopean",
    coordinate_units = "normalized",
    screen_distance_m = 0.6,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1920, 1080),
    screen_size_m = c(0.53, 0.30)
  )

  preview <- export_gazepoint_to_bids(
    gaze,
    bids_root = root,
    subject = "08",
    task = "viewing",
    recorded_eye = "cyclopean",
    coordinate_units = "normalized",
    dry_run = TRUE
  )

  expect_false(preview$audit$ready_to_write)
  expect_true(any(preview$files$action == "conflict"))

  expect_error(
    export_gazepoint_to_bids(
      gaze,
      bids_root = root,
      subject = "08",
      task = "viewing",
      recorded_eye = "cyclopean",
      coordinate_units = "normalized"
    ),
    "already exists"
  )

  expect_true(all(file.exists(first$files$path)))

  unlink(root, recursive = TRUE, force = TRUE)
})

test_that("existing dataset and events metadata support another eye", {
  skip_if_not_installed("jsonlite")

  root <- tempfile("bids-binocular-")

  left <- data.frame(
    TIME = c(0, 0.1, 0.2),
    LPOGX = c(0.4, 0.5, 0.6),
    LPOGY = c(0.5, 0.6, 0.7)
  )

  right <- data.frame(
    TIME = c(0, 0.1, 0.2),
    RPOGX = c(0.45, 0.55, 0.65),
    RPOGY = c(0.55, 0.65, 0.75)
  )

  export_gazepoint_to_bids(
    left,
    bids_root = root,
    subject = "09",
    task = "viewing",
    dataset_name = "Binocular study",
    recorded_eye = "left",
    recording = "eye1",
    coordinate_units = "normalized",
    screen_distance_m = 0.6,
    screen_origin = c("top", "left"),
    screen_resolution_px = c(1920, 1080),
    screen_size_m = c(0.53, 0.30)
  )

  second <- export_gazepoint_to_bids(
    right,
    bids_root = root,
    subject = "09",
    task = "viewing",
    recorded_eye = "right",
    recording = "eye2",
    coordinate_units = "normalized"
  )

  expect_true(any(
    second$files$role == "dataset_description" &
      second$files$action == "reuse"
  ))

  expect_true(any(
    second$files$role == "events_json" &
      second$files$action == "reuse"
  ))

  expect_true(any(grepl(
    "recording-eye2",
    second$files$path
  )))

  unlink(root, recursive = TRUE, force = TRUE)
})

test_that("BIDS labels and source columns are validated", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2),
    BPOGX = c(0.4, 0.5, 0.6),
    BPOGY = c(0.5, 0.6, 0.7)
  )

  expect_error(
    export_gazepoint_to_bids(
      gaze,
      bids_root = tempfile("bids-label-"),
      subject = "sub-01",
      task = "viewing",
      dataset_name = "Invalid subject",
      recorded_eye = "cyclopean",
      sample_coordinate_system = "eye-in-head",
      coordinate_units = "degree",
      dry_run = TRUE
    ),
    "letters and numbers"
  )

  expect_error(
    export_gazepoint_to_bids(
      gaze,
      bids_root = tempfile("bids-column-"),
      subject = "10",
      task = "viewing",
      dataset_name = "Missing column",
      recorded_eye = "cyclopean",
      x_col = "missing_x",
      sample_coordinate_system = "eye-in-head",
      coordinate_units = "degree",
      dry_run = TRUE
    ),
    "was not found"
  )
})

test_that("custom coordinate systems require a description", {
  skip_if_not_installed("jsonlite")

  gaze <- data.frame(
    TIME = c(0, 0.1, 0.2),
    BPOGX = c(0.4, 0.5, 0.6),
    BPOGY = c(0.5, 0.6, 0.7)
  )

  expect_error(
    export_gazepoint_to_bids(
      gaze,
      bids_root = tempfile("bids-custom-"),
      subject = "11",
      task = "viewing",
      dataset_name = "Custom system",
      recorded_eye = "cyclopean",
      sample_coordinate_system = "custom",
      coordinate_units = "arbitrary",
      dry_run = TRUE
    ),
    "custom_coordinate_system_description"
  )

  out <- export_gazepoint_to_bids(
    gaze,
    bids_root = tempfile("bids-custom-ok-"),
    subject = "11",
    task = "viewing",
    dataset_name = "Custom system",
    recorded_eye = "cyclopean",
    sample_coordinate_system = "custom",
    custom_coordinate_system_description =
      "Device-specific normalized display plane.",
    coordinate_units = "arbitrary",
    dry_run = TRUE
  )

  expect_match(
    out$physio_sidecar$SampleCoordinateSystemDescription,
    "Device-specific"
  )
})
