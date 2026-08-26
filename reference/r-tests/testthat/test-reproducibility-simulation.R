test_that("simulate_gazepoint_artifact injects reproducible missing runs", {
  dat <- data.frame(
    participant = rep(c("P01", "P02"), each = 10),
    time_ms = seq(0, 1900, by = 100),
    pupil = seq(3.0, 3.19, length.out = 20),
    gsr = seq(0.7, 0.89, length.out = 20)
  )

  sim1 <- simulate_gazepoint_artifact(
    dat,
    signal_cols = c("pupil", "gsr"),
    artifact = "missing_run",
    n_artifacts = 1,
    artifact_length = 3,
    seed = 10
  )

  sim2 <- simulate_gazepoint_artifact(
    dat,
    signal_cols = c("pupil", "gsr"),
    artifact = "missing_run",
    n_artifacts = 1,
    artifact_length = 3,
    seed = 10
  )

  expect_s3_class(sim1, "gazepoint_artifact_simulation")
  expect_equal(sim1$artifact_log, sim2$artifact_log)
  expect_equal(sim1$data, sim2$data)
  expect_true(all(c("pupil_artifact", "gsr_artifact") %in% names(sim1$data)))
  expect_equal(nrow(sim1$artifact_log), 2)
  expect_equal(sim1$artifact_log$n_samples_modified, c(3L, 3L))
  expect_true(any(is.na(sim1$data$pupil_artifact)))
  expect_true(any(is.na(sim1$data$gsr_artifact)))
})

test_that("simulate_gazepoint_artifact supports flatline, spike, noise, drift, and overwrite", {
  dat <- data.frame(
    time_ms = seq(0, 900, by = 100),
    pupil = seq(3.0, 3.9, length.out = 10)
  )

  sim <- simulate_gazepoint_artifact(
    dat,
    signal_cols = "pupil",
    artifact = c("flatline", "spike", "noise", "drift"),
    n_artifacts = 1,
    artifact_length = 2,
    magnitude = 1,
    seed = 99
  )

  expect_equal(nrow(sim$artifact_log), 4)
  expect_true("pupil_artifact" %in% names(sim$data))
  expect_true(any(sim$data$pupil_artifact != dat$pupil, na.rm = TRUE))

  overwritten <- simulate_gazepoint_artifact(
    dat,
    signal_cols = "pupil",
    artifact = "drift",
    n_artifacts = 1,
    artifact_length = 3,
    magnitude = 1,
    seed = 1,
    overwrite = TRUE
  )

  expect_false("pupil_artifact" %in% names(overwritten$data))
  expect_true(any(overwritten$data$pupil != dat$pupil, na.rm = TRUE))
})

test_that("simulate_gazepoint_artifact validates inputs", {
  dat <- data.frame(
    pupil = c(3.1, 3.2),
    label = c("a", "b")
  )

  expect_error(
    simulate_gazepoint_artifact(dat, signal_cols = "missing"),
    "not found"
  )

  expect_error(
    simulate_gazepoint_artifact(dat, signal_cols = "label"),
    "numeric"
  )

  expect_error(
    simulate_gazepoint_artifact(dat, signal_cols = "pupil", n_artifacts = -1),
    "non-negative"
  )

  existing <- data.frame(pupil = c(3.1, 3.2), pupil_artifact = c(0, 0))
  expect_error(
    simulate_gazepoint_artifact(existing, signal_cols = "pupil"),
    "already exists"
  )
})

test_that("generate_gazepoint_manifest records file metadata and writes outputs", {
  txt_path <- tempfile(fileext = ".txt")
  existing_path <- tempfile(fileext = ".csv")
  writeLines(c("participant,time_ms", "P01,0"), existing_path)
  rds_path <- tempfile(fileext = ".rds")

  manifest <- generate_gazepoint_manifest(
    input_paths = c(existing_path, "missing_file.csv"),
    parameters = list(step = "unit-test", threshold = 0.2),
    outputs = "qc_table",
    notes = "Synthetic test only",
    write_path = txt_path,
    include_session_info = FALSE
  )

  expect_s3_class(manifest, "gazepoint_manifest")
  expect_true(file.exists(txt_path))
  expect_equal(nrow(manifest$input_files), 2)
  expect_true(manifest$input_files$exists[1])
  expect_false(manifest$input_files$exists[2])
  expect_null(manifest$session_info)

  manifest_rds <- generate_gazepoint_manifest(
    parameters = list(step = "rds-test"),
    write_path = rds_path,
    include_session_info = FALSE
  )

  expect_true(file.exists(rds_path))
  expect_s3_class(readRDS(rds_path), "gazepoint_manifest")
  expect_equal(manifest_rds$parameters$step, "rds-test")

  expect_error(
    generate_gazepoint_manifest(parameters = "bad"),
    "list"
  )
})

test_that("create_gazepoint_dictionary summarizes data frames", {
  dat <- data.frame(
    participant = c("P01", "P02", NA),
    trial = c(1, 1, 2),
    pupil = c(3.1, NA, 3.2)
  )

  dictionary <- create_gazepoint_dictionary(
    dat,
    units = c(pupil = "arbitrary unit"),
    descriptions = c(participant = "Participant code"),
    required_cols = c("participant", "trial", "time_ms")
  )

  expect_s3_class(dictionary, "gazepoint_dictionary")
  expect_true(all(c(
    "source",
    "column",
    "present",
    "required",
    "type",
    "n_missing",
    "prop_missing",
    "unit",
    "description"
  ) %in% names(dictionary)))
  expect_true("time_ms" %in% dictionary$column)
  expect_false(dictionary$present[dictionary$column == "time_ms"])
  expect_equal(dictionary$unit[dictionary$column == "pupil"], "arbitrary unit")
  expect_equal(
    dictionary$description[dictionary$column == "participant"],
    "Participant code"
  )
})

test_that("create_gazepoint_dictionary reads CSV headers and writes files", {
  csv_path <- tempfile(fileext = ".csv")
  out_csv <- tempfile(fileext = ".csv")
  out_md <- tempfile(fileext = ".md")

  utils::write.csv(
    data.frame(participant = "P01", time_ms = 0, gsr = 0.7),
    csv_path,
    row.names = FALSE
  )

  dictionary <- create_gazepoint_dictionary(
    file_paths = csv_path,
    required_cols = c("participant", "time_ms", "pupil"),
    write_path = out_csv
  )

  expect_true(file.exists(out_csv))
  expect_true("pupil" %in% dictionary$column)
  expect_false(dictionary$present[dictionary$column == "pupil"])

  dictionary_md <- create_gazepoint_dictionary(
    file_paths = csv_path,
    required_cols = "participant",
    write_path = out_md
  )

  expect_true(file.exists(out_md))
  expect_s3_class(dictionary_md, "gazepoint_dictionary")

  expect_error(
    create_gazepoint_dictionary(),
    "Supply either"
  )

  expect_error(
    create_gazepoint_dictionary(
      data.frame(x = 1),
      units = c("missing-name")
    ),
    "must have names"
  )
})

test_that("anonymize_gazepoint_data pseudonymizes identifiers deterministically", {
  dat <- data.frame(
    participant = c("S02", "S01", "S02", NA),
    session = c("B", "A", "B", "C"),
    value = 1:4
  )

  anon <- anonymize_gazepoint_data(
    dat,
    id_cols = c("participant", "session"),
    prefix = "ID",
    width = 2
  )

  expect_s3_class(anon, "gazepoint_anonymized_data")
  expect_equal(anon$participant, c("ID02", "ID01", "ID02", NA))
  expect_equal(anon$session, c("ID02", "ID01", "ID02", "ID03"))
  expect_true(!is.null(attr(anon, "id_mapping")))
  expect_true(all(c("column", "original_value", "anonymized_value") %in% names(attr(anon, "id_mapping"))))

  anon_no_map <- anonymize_gazepoint_data(
    dat,
    id_cols = "participant",
    keep_mapping = FALSE
  )

  expect_null(attr(anon_no_map, "id_mapping"))

  expect_error(
    anonymize_gazepoint_data(dat, id_cols = "missing"),
    "not found"
  )
})
