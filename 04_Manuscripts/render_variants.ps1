$ErrorActionPreference = "Stop"

quarto render "variants/submission.qmd" --output-dir "outputs/submission"
quarto render "variants/preprint.qmd" --output-dir "outputs/preprint"
