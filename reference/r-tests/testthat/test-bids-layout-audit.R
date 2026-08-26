test_that("check_gazepoint_bids detects a simple BIDS-like Gazepoint layout", {
  root <- tempfile("gp_bids_")
  dir.create(root)
  writeLines('{"Name":"Synthetic Gazepoint dataset"}', file.path(root, "dataset_description.json"))
  writeLines(c("participant_id", "sub-001"), file.path(root, "participants.tsv"))
  dir.create(file.path(root, "sub-001"))
  dir.create(file.path(root, "sub-001", "gazepoint"))
  utils::write.csv(
    data.frame(time = 1:3, pupil = c(2.1, 2.2, 2.3)),
    file.path(root, "sub-001", "gazepoint", "sub-001_task-demo_all_gaze.csv"),
    row.names = FALSE
  )

  out <- check_gazepoint_bids(root)

  expect_s3_class(out, "gazepoint_bids_layout_audit")
  expect_equal(out$summary$n_fail, 0)
  expect_true(any(out$checks$check == "gazepoint_export_files" & out$checks$status == "pass"))
  expect_true(any(out$checks$check == "subject_directories" & out$checks$status == "pass"))
})

test_that("check_gazepoint_bids reports a missing root as a failure", {
  missing_root <- file.path(tempdir(), "definitely_missing_gazepoint_bids_root")

  out <- check_gazepoint_bids(missing_root)

  expect_s3_class(out, "gazepoint_bids_layout_audit")
  expect_true(any(out$checks$check == "root_directory" & out$checks$status == "fail"))
  expect_false(out$summary$layout_ready)
})

test_that("check_gazepoint_bids warns on sparse folders without Gazepoint exports", {
  root <- tempfile("gp_sparse_")
  dir.create(root)

  out <- check_gazepoint_bids(root)

  expect_s3_class(out, "gazepoint_bids_layout_audit")
  expect_equal(out$summary$n_fail, 0)
  expect_true(out$summary$needs_review)
  expect_true(any(out$checks$status == "warn"))
})
