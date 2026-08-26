test_that("formatted feature inventory preserves all functions and adds user-facing metadata", {
  inventory <- create_gazepoint_biometrics_feature_inventory()
  formatted <- format_gazepoint_biometrics_feature_inventory(inventory)

  expect_s3_class(formatted, "data.frame")
  expect_equal(nrow(formatted), nrow(inventory$inventory))

  expected_cols <- c(
    "domain",
    "domain_label",
    "workflow_stage",
    "method_family",
    "user_level",
    "function_name",
    "interpretation_caution",
    "available",
    "availability_label",
    "status"
  )

  expect_true(all(expected_cols %in% names(formatted)))
  expect_true(all(formatted$available))
  expect_true(all(formatted$availability_label == "Available"))
  expect_true(all(nchar(formatted$domain_label) > 0))
  expect_true(all(nchar(formatted$method_family) > 0))
  expect_true(all(nchar(formatted$interpretation_caution) > 0))
})

test_that("formatted feature inventory summary reports complete coverage", {
  formatted <- format_gazepoint_biometrics_feature_inventory()
  summary <- summarise_gazepoint_biometrics_feature_inventory(formatted)

  expect_named(
    summary,
    c("overview", "domain_summary", "method_summary", "user_level_summary")
  )

  expect_equal(summary$overview$status, "formatted_inventory_complete")
  expect_equal(summary$overview$feature_rows, nrow(formatted))
  expect_equal(summary$overview$missing_features, 0)
  expect_true(all(summary$domain_summary$status == "complete"))
})
