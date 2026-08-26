#' Create a Gazepoint biometrics preregistration template
#'
#' Creates a cautious preregistration template for Gazepoint Biometrics EDA/GSR
#' workflows.
#'
#' @param study_title Study title.
#' @param signal_standardization Standardization plan.
#' @param artifact_rules Artifact-rule description.
#' @param eda_min_us Minimum conductance threshold.
#' @param eda_max_us Maximum conductance threshold.
#' @param rapid_change_threshold Maximum absolute percent change per second.
#' @param output_file Optional path to write the template as a text file.
#'
#' @return A character string.
#' @export
create_gazepoint_preregistration_template <- function(study_title = "Gazepoint biometrics study",
                                                      signal_standardization = c("within_participant_z", "range_correction", "none"),
                                                      artifact_rules = c("kleckner_style", "custom", "none"),
                                                      eda_min_us = 0.01,
                                                      eda_max_us = 100,
                                                      rapid_change_threshold = 20,
                                                      output_file = NULL) {
  signal_standardization <- match.arg(signal_standardization)
  artifact_rules <- match.arg(artifact_rules)

  standardization_text <- switch(
    signal_standardization,
    within_participant_z = paste(
      "Biometric responses will be standardised within participant using z-scoring:",
      "z = (x - participant mean) / participant standard deviation.",
      "This transformation is intended to support within-participant comparison and will be reported as removing between-participant level and scale differences."
    ),
    range_correction = paste(
      "Biometric responses will be range-corrected within participant:",
      "(x - participant minimum) / (participant maximum - participant minimum).",
      "This transformation is intended to express responses as a proportion of each participant's observed signal range."
    ),
    none = "No participant-level signal standardisation will be applied before the primary model unless specified in a sensitivity analysis."
  )

  artifact_text <- switch(
    artifact_rules,
    kleckner_style = paste(
      "EDA artifacts will be flagged using transparent Kleckner-style heuristic rules:",
      "non-finite samples, conductance values outside the planned physiological range, rapid absolute percent changes per second,",
      "and transition padding around bad samples.",
      "The planned conductance range is",
      paste0("[", eda_min_us, ", ", eda_max_us, "] microsiemens"),
      "and the planned rapid-change threshold is",
      paste0(rapid_change_threshold, "% per second.")
    ),
    custom = "EDA artifacts will be flagged using study-specific rules defined before analysis and reported with thresholds and exclusion counts.",
    none = "No automated EDA artifact rule will be applied before analysis; manual or visual quality checks will be reported if used."
  )

  text <- paste(
    "# Preregistration template:",
    study_title,
    "",
    "## Data source",
    "Raw Gazepoint Biometrics exports will be imported using gpbiometrics. The analysis will report imported file counts, detected biometric channels, detected time columns, detected timebase, and available TTL/event markers.",
    "",
    "## Quality control",
    "Before statistical analysis, the data will be audited for missingness, inactive or all-zero channels, grouped counter resets, row-order problems, EDA artifacts, and usable signal coverage.",
    "",
    "## EDA preprocessing",
    "GSR/EDA conductance conversion will be applied only when the unit assumptions are explicit. The analysis will report smoothing, baseline-correction, SCR peak-detection, and event-window settings.",
    "",
    "## Standardisation plan",
    standardization_text,
    "",
    "## Artifact rules",
    artifact_text,
    "",
    "## SCR interval windows",
    "If SCR latency-window analysis is used, responses will be classified into FIR, SIR, and TIR windows using prespecified latency boundaries. These labels will be treated as latency descriptors, not emotion or diagnosis labels.",
    "",
    "## Statistical modelling",
    "SCR occurrence/amplitude and continuous SCL/EDA outcomes will be analysed using model-ready tables prepared by gpbiometrics. Hurdle or mixed-effects models will be fitted outside gpbiometrics in appropriate modelling packages.",
    "",
    "## Interpretation guardrail",
    "EDA/GSR, heart-rate, pupil, and gaze measures will not be interpreted as direct evidence of emotion, valence, stress, trust, preference, cognition, or diagnosis without converging design, behavioural, and self-report evidence.",
    sep = "\n"
  )

  if (!is.null(output_file)) {
    writeLines(text, con = output_file, useBytes = TRUE)
  }

  text
}

#' Launch a lightweight gpbiometrics Shiny dashboard
#'
#' Launches an optional local Shiny interface for inspecting a Gazepoint
#' Biometrics CSV file. Shiny is optional and is not required to use the package.
#'
#' @return A Shiny application object, launched for interactive use.
#' @export
run_gpbiometrics_shiny <- function() {
  if (!requireNamespace("shiny", quietly = TRUE)) {
    stop(
      "The optional package `shiny` is required. Install it with install.packages('shiny').",
      call. = FALSE
    )
  }

  ui <- shiny::fluidPage(
    shiny::titlePanel("gpbiometrics local QC dashboard"),
    shiny::sidebarLayout(
      shiny::sidebarPanel(
        shiny::fileInput("file", "Upload Gazepoint CSV", accept = c(".csv", ".txt")),
        shiny::textInput("time_col", "Time column", value = "CNT"),
        shiny::textInput("signal_cols", "Signal columns, comma-separated", value = "GSR_US, HR, IBI, DIAL"),
        shiny::actionButton("run", "Run QC")
      ),
      shiny::mainPanel(
        shiny::h4("Preview"),
        shiny::tableOutput("preview"),
        shiny::h4("Signal activity"),
        shiny::verbatimTextOutput("activity"),
        shiny::h4("Notes"),
        shiny::verbatimTextOutput("notes")
      )
    )
  )

  server <- function(input, output, session) {
    dat <- shiny::reactive({
      req <- input$file

      if (is.null(req)) {
        return(NULL)
      }

      utils::read.csv(req$datapath, stringsAsFactors = FALSE, check.names = FALSE)
    })

    output$preview <- shiny::renderTable({
      x <- dat()
      if (is.null(x)) {
        return(NULL)
      }
      utils::head(x)
    })

    qc <- shiny::eventReactive(input$run, {
      x <- dat()

      if (is.null(x)) {
        return("Upload a file first.")
      }

      signal_cols <- trimws(strsplit(input$signal_cols, ",")[[1]])
      signal_cols <- intersect(signal_cols, names(x))

      if (length(signal_cols) == 0) {
        return("No requested signal columns were found.")
      }

      audit <- audit_gazepoint_signal_activity(
        x,
        signal_cols = signal_cols
      )

      utils::capture.output(print(audit))
    })

    output$activity <- shiny::renderText({
      paste(qc(), collapse = "\n")
    })

    output$notes <- shiny::renderText({
      paste(
        "This GUI is a lightweight local helper.",
        "It supports quick inspection only and does not infer emotion, valence, stress, trust, preference, cognition, or diagnosis.",
        sep = "\n"
      )
    })
  }

  shiny::shinyApp(ui = ui, server = server)
}
