test_that("summarize_gazepoint_export_inventory inventories and classifies files", {
  tmp <- file.path(tempdir(), "gp_dataset_inventory_test")
  unlink(tmp, recursive = TRUE)
  dir.create(file.path(tmp, "sub-P01"), recursive = TRUE)
  dir.create(file.path(tmp, "sub-P02"), recursive = TRUE)

  write.csv(
    data.frame(time = 1:3, pupil_left = c(3.1, 0, 3.2)),
    file.path(tmp, "sub-P01", "P01_all_gaze.csv"),
    row.names = FALSE
  )
  writeLines("{}", file.path(tmp, "sub-P01", "P01_all_gaze.json"))
  write.csv(
    data.frame(fixation = 1:2),
    file.path(tmp, "sub-P01", "P01_fixations.csv"),
    row.names = FALSE
  )
  file.create(file.path(tmp, "sub-P02", "P02_all_gaze.csv"))
  writeLines("bad extension", file.path(tmp, "sub-P02", "notes.tmp"))

  inventory <- summarize_gazepoint_export_inventory(tmp)

  expect_s3_class(inventory, "gazepoint_export_inventory")
  expect_equal(nrow(inventory), 5)
  expect_true(all(c(
    "path", "relative_path", "directory", "file_name", "extension",
    "size_bytes", "modified_time", "is_empty", "likely_export_type",
    "participant_id", "has_sidecar"
  ) %in% names(inventory)))

  gaze <- inventory[inventory$file_name == "P01_all_gaze.csv", ]
  sidecar <- inventory[inventory$file_name == "P01_all_gaze.json", ]
  empty <- inventory[inventory$file_name == "P02_all_gaze.csv", ]
  notes <- inventory[inventory$file_name == "notes.tmp", ]

  expect_equal(gaze$likely_export_type, "all_gaze")
  expect_equal(sidecar$likely_export_type, "sidecar")
  expect_equal(notes$likely_export_type, "unknown")
  expect_true(gaze$has_sidecar)
  expect_true(sidecar$has_sidecar)
  expect_false(empty$has_sidecar)
  expect_true(empty$is_empty)
  expect_equal(gaze$participant_id, "sub-P01")
})

test_that("summarize_gazepoint_export_inventory handles file vectors and empty folders", {
  tmp <- file.path(tempdir(), "gp_dataset_inventory_vector_test")
  unlink(tmp, recursive = TRUE)
  dir.create(tmp, recursive = TRUE)
  empty_dir <- file.path(tmp, "empty")
  dir.create(empty_dir)

  empty_inventory <- summarize_gazepoint_export_inventory(empty_dir)
  expect_s3_class(empty_inventory, "gazepoint_export_inventory")
  expect_equal(nrow(empty_inventory), 0)

  f1 <- file.path(tmp, "events.tsv")
  f2 <- file.path(tmp, "eda_biometrics.csv")
  writeLines("onset\ttrial", f1)
  write.csv(data.frame(eda = 1:2), f2, row.names = FALSE)

  inventory <- summarize_gazepoint_export_inventory(c(f1, f2), recursive = FALSE)
  expect_equal(nrow(inventory), 2)
  expect_true("events" %in% inventory$likely_export_type)
  expect_true("biometrics" %in% inventory$likely_export_type)
})

test_that("audit_gazepoint_dataset_structure reports expected structural checks", {
  tmp <- file.path(tempdir(), "gp_dataset_audit_test")
  unlink(tmp, recursive = TRUE)
  dir.create(file.path(tmp, "sub-P01"), recursive = TRUE)
  dir.create(file.path(tmp, "sub-P02"), recursive = TRUE)
  dir.create(file.path(tmp, "metadata"), recursive = TRUE)

  write.csv(
    data.frame(time = 1:3, pupil_left = c(3.1, 0, 3.2)),
    file.path(tmp, "sub-P01", "P01_all_gaze.csv"),
    row.names = FALSE
  )
  write.csv(
    data.frame(fixation = 1:2),
    file.path(tmp, "sub-P01", "P01_fixations.csv"),
    row.names = FALSE
  )
  writeLines("{}", file.path(tmp, "sub-P01", "P01_all_gaze.json"))
  file.create(file.path(tmp, "sub-P02", "P02_all_gaze.csv"))
  writeLines("bad extension", file.path(tmp, "sub-P02", "notes.tmp"))

  audit <- audit_gazepoint_dataset_structure(
    tmp,
    expected_dirs = c("sub-P01", "sub-P02", "metadata", "missing_dir"),
    expected_files = c("sub-P01/P01_all_gaze.csv", "metadata/dataset_description.json"),
    expected_patterns = c(all_gaze = "all_gaze", fixation = "fixation", summary = "summary"),
    allowed_extensions = c("csv", "json"),
    require_sidecars = TRUE
  )

  expect_s3_class(audit, "gazepoint_dataset_structure_audit")
  expect_named(audit, c("root", "inventory", "checks", "summary", "parameters"))
  expect_equal(audit$summary$n_files, 5)
  expect_equal(audit$summary$n_fail, 4)
  expect_equal(audit$summary$n_warn, 4)
  expect_false(audit$summary$audit_pass)

  checks <- audit$checks
  expect_true(any(checks$check == "expected_dirs" & checks$item == "missing_dir" & checks$status == "fail"))
  expect_true(any(checks$check == "expected_files" & checks$item == "metadata/dataset_description.json" & checks$status == "fail"))
  expect_true(any(checks$check == "expected_patterns" & checks$item == "summary" & checks$status == "fail"))
  expect_true(any(checks$check == "empty_files" & checks$item == "P02_all_gaze.csv" & checks$status == "fail"))
  expect_true(any(checks$check == "unexpected_extensions" & checks$item == "tmp" & checks$status == "warn"))
  expect_true(any(checks$check == "sidecars" & checks$item == "P02_all_gaze.csv" & checks$status == "warn"))
})

test_that("audit_gazepoint_dataset_structure can pass clean simple datasets", {
  tmp <- file.path(tempdir(), "gp_dataset_clean_audit_test")
  unlink(tmp, recursive = TRUE)
  dir.create(file.path(tmp, "sub-P01"), recursive = TRUE)

  write.csv(data.frame(time = 1:3), file.path(tmp, "sub-P01", "P01_all_gaze.csv"), row.names = FALSE)
  writeLines("{}", file.path(tmp, "sub-P01", "P01_all_gaze.json"))

  audit <- audit_gazepoint_dataset_structure(
    tmp,
    expected_dirs = "sub-P01",
    expected_files = "sub-P01/P01_all_gaze.csv",
    expected_patterns = c(all_gaze = "all_gaze"),
    allowed_extensions = c("csv", "json"),
    require_sidecars = TRUE
  )

  expect_equal(audit$summary$n_fail, 0)
  expect_equal(audit$summary$n_warn, 0)
  expect_true(audit$summary$audit_pass)
})

test_that("create_gazepoint_sidecar_template creates default and custom metadata fields", {
  sidecar <- create_gazepoint_sidecar_template(
    dataset_id = "demo",
    export_type = "all_gaze",
    include_optional = TRUE,
    custom_fields = data.frame(
      field = "calibration_notes",
      description = "Notes about calibration quality.",
      required = FALSE,
      value = "",
      notes = ""
    )
  )

  expect_s3_class(sidecar, "gazepoint_sidecar_template")
  expect_true(all(c("field", "description", "required", "value", "notes") %in% names(sidecar)))
  expect_true("dataset_id" %in% sidecar$field)
  expect_true("export_type" %in% sidecar$field)
  expect_true("calibration_notes" %in% sidecar$field)
  expect_equal(sidecar$value[sidecar$field == "dataset_id"], "demo")
  expect_equal(sidecar$value[sidecar$field == "export_type"], "all_gaze")
  expect_equal(sum(sidecar$required), 9)

  required_only <- create_gazepoint_sidecar_template(include_optional = FALSE)
  expect_equal(nrow(required_only), 9)
  expect_true(all(required_only$required))
})

test_that("dataset structure helpers validate inputs", {
  tmp <- file.path(tempdir(), "gp_dataset_validation_test")
  unlink(tmp, recursive = TRUE)
  dir.create(tmp, recursive = TRUE)
  writeLines("x", file.path(tmp, "file.csv"))

  expect_error(summarize_gazepoint_export_inventory(character(0)), "path")
  expect_error(summarize_gazepoint_export_inventory(file.path(tmp, "missing.csv")), "not found")
  expect_error(summarize_gazepoint_export_inventory(tmp, recursive = NA), "recursive")

  expect_error(audit_gazepoint_dataset_structure(file.path(tmp, "missing")), "root")
  expect_error(audit_gazepoint_dataset_structure(tmp, expected_dirs = 1), "expected_dirs")
  expect_error(audit_gazepoint_dataset_structure(tmp, require_sidecars = NA), "require_sidecars")

  expect_error(create_gazepoint_sidecar_template(dataset_id = c("a", "b")), "dataset_id")
  expect_error(create_gazepoint_sidecar_template(export_type = c("a", "b")), "export_type")
  expect_error(create_gazepoint_sidecar_template(include_optional = NA), "include_optional")
  expect_error(create_gazepoint_sidecar_template(custom_fields = data.frame(field = "x")), "missing required")
})
