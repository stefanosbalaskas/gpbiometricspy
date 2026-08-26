#' Launch a lightweight gpbiometrics Shiny peak/artifact annotator
#'
#' Launches a local Shiny app for manual EDA peak/artifact annotation. The app
#' lets users upload a Gazepoint CSV, inspect a selected signal, enter manual
#' peak/artifact intervals, and download annotation CSVs.
#'
#' This is an optional local GUI helper. It does not replace automated scoring
#' or infer emotion, stress, cognition, trust, preference, or diagnosis.
#'
#' @return A Shiny application object, launched for interactive use.
#' @export
run_gpbiometrics_shiny_annotator <- function() {
  if (!requireNamespace("shiny", quietly = TRUE)) {
    stop(
      "The optional package `shiny` is required. Install it with install.packages('shiny').",
      call. = FALSE
    )
  }

  ui <- shiny::fluidPage(
    shiny::titlePanel("gpbiometrics EDA annotator"),
    shiny::sidebarLayout(
      shiny::sidebarPanel(
        shiny::fileInput("file", "Upload Gazepoint CSV", accept = c(".csv", ".txt")),
        shiny::textInput("time_col", "Time column", value = "CNT"),
        shiny::textInput("signal_col", "EDA signal column", value = "GSR_US"),
        shiny::numericInput("peak_time", "Manual peak time", value = NA),
        shiny::numericInput("artifact_start", "Artifact start", value = NA),
        shiny::numericInput("artifact_end", "Artifact end", value = NA),
        shiny::textInput("note", "Annotation note", value = ""),
        shiny::actionButton("add_peak", "Add manual peak"),
        shiny::actionButton("add_artifact", "Add artifact interval"),
        shiny::downloadButton("download_annotations", "Download annotations")
      ),
      shiny::mainPanel(
        shiny::plotOutput("eda_plot", click = "plot_click", height = "350px"),
        shiny::h4("Click position"),
        shiny::verbatimTextOutput("click_info"),
        shiny::h4("Annotations"),
        shiny::tableOutput("annotation_table"),
        shiny::h4("Interpretation guardrail"),
        shiny::verbatimTextOutput("guardrail")
      )
    )
  )

  server <- function(input, output, session) {
    dat <- shiny::reactive({
      req <- input$file
      if (is.null(req)) return(NULL)
      utils::read.csv(req$datapath, stringsAsFactors = FALSE, check.names = FALSE)
    })

    annotations <- shiny::reactiveVal(data.frame(
      annotation_type = character(),
      time = numeric(),
      start = numeric(),
      end = numeric(),
      note = character(),
      stringsAsFactors = FALSE
    ))

    output$eda_plot <- shiny::renderPlot({
      x <- dat()
      if (is.null(x)) return(NULL)
      if (!input$time_col %in% names(x) || !input$signal_col %in% names(x)) return(NULL)

      graphics::plot(
        x[[input$time_col]],
        x[[input$signal_col]],
        type = "l",
        xlab = input$time_col,
        ylab = input$signal_col,
        main = "Manual EDA annotation"
      )

      ann <- annotations()

      peaks <- ann[ann$annotation_type == "manual_peak", , drop = FALSE]
      if (nrow(peaks) > 0) {
        graphics::abline(v = peaks$time, lty = 2)
      }

      arts <- ann[ann$annotation_type == "artifact_interval", , drop = FALSE]
      if (nrow(arts) > 0) {
        for (i in seq_len(nrow(arts))) {
          graphics::rect(
            xleft = arts$start[i],
            ybottom = grDevices::extendrange(x[[input$signal_col]])[1],
            xright = arts$end[i],
            ytop = grDevices::extendrange(x[[input$signal_col]])[2],
            density = 12,
            border = NA
          )
        }
      }
    })

    output$click_info <- shiny::renderPrint({
      input$plot_click
    })

    shiny::observeEvent(input$add_peak, {
      ann <- annotations()
      new <- data.frame(
        annotation_type = "manual_peak",
        time = input$peak_time,
        start = NA_real_,
        end = NA_real_,
        note = input$note,
        stringsAsFactors = FALSE
      )
      annotations(rbind(ann, new))
    })

    shiny::observeEvent(input$add_artifact, {
      ann <- annotations()
      new <- data.frame(
        annotation_type = "artifact_interval",
        time = NA_real_,
        start = input$artifact_start,
        end = input$artifact_end,
        note = input$note,
        stringsAsFactors = FALSE
      )
      annotations(rbind(ann, new))
    })

    output$annotation_table <- shiny::renderTable({
      annotations()
    })

    output$download_annotations <- shiny::downloadHandler(
      filename = function() {
        "gpbiometrics_manual_annotations.csv"
      },
      content = function(file) {
        utils::write.csv(annotations(), file, row.names = FALSE)
      }
    )

    output$guardrail <- shiny::renderText({
      paste(
        "Manual annotations are expert review metadata.",
        "They do not infer emotion, stress, cognition, trust, preference, or diagnosis.",
        sep = "\n"
      )
    })
  }

  shiny::shinyApp(ui = ui, server = server)
}
