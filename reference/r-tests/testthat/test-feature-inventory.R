test_that("create_gazepoint_biometrics_feature_inventory returns structured outputs", {
  res <- create_gazepoint_biometrics_feature_inventory()

  expect_s3_class(res, "gazepoint_biometrics_feature_inventory")
  expect_true(is.data.frame(res$overview))
  expect_true(is.data.frame(res$inventory))
  expect_true(is.data.frame(res$domain_summary))
  expect_true(is.data.frame(res$missing_expected))
  expect_true(is.list(res$settings))

  expect_true(all(c(
    "domain",
    "function_name",
    "available",
    "status"
  ) %in% names(res$inventory)))

  expect_true(all(c(
    "domain",
    "feature_count",
    "available_features",
    "missing_features",
    "completion_rate",
    "status"
  ) %in% names(res$domain_summary)))
})

test_that("feature inventory includes recent helper domains", {
  res <- create_gazepoint_biometrics_feature_inventory()

  expect_true("aoi_biometrics" %in% res$inventory$domain)
  expect_true("interoperability" %in% res$inventory$domain)
  expect_true("plotting" %in% res$inventory$domain)
  expect_true("eda_scr" %in% res$inventory$domain)
  expect_true("ibi_hr_hrv" %in% res$inventory$domain)

  expect_true("summarise_gazepoint_aoi_biometrics" %in% res$inventory$function_name)
  expect_true("export_gazepoint_rhrv_input" %in% res$inventory$function_name)
  expect_true("standardise_gazepoint_plot_contract" %in% res$inventory$function_name)
})

test_that("feature inventory detects available exported functions", {
  res <- create_gazepoint_biometrics_feature_inventory()

  selected <- res$inventory[
    res$inventory$function_name %in% c(
      "summarise_gazepoint_aoi_biometrics",
      "prepare_gazepoint_aoi_biometrics_model_data",
      "plot_gazepoint_aoi_biometrics",
      "export_gazepoint_rhrv_input",
      "prepare_gazepoint_neurokit_eda_input",
      "run_gazepoint_neurokit_eda_crosscheck",
      "standardise_gazepoint_plot_contract",
      "check_gazepoint_plot_contract"
    ),
    ,
    drop = FALSE
  ]

  expect_equal(nrow(selected), 8)
  expect_true(all(selected$available))
  expect_true(all(selected$status == "available"))
})

test_that("feature inventory domain summary is internally consistent", {
  res <- create_gazepoint_biometrics_feature_inventory()

  expect_equal(
    sum(res$domain_summary$feature_count),
    nrow(res$inventory)
  )

  expect_equal(
    sum(res$domain_summary$available_features),
    sum(res$inventory$available)
  )

  expect_true(all(res$domain_summary$completion_rate >= 0))
  expect_true(all(res$domain_summary$completion_rate <= 1))
})

test_that("feature inventory validates inputs", {
  expect_error(
    create_gazepoint_biometrics_feature_inventory(include_internal = NA),
    "`include_internal` must be TRUE or FALSE"
  )
})
