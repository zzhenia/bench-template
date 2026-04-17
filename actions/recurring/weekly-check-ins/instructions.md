# Weekly Check-ins

A recurring action that runs every Monday to summarise the previous week's work.

## How to use

Configure your time tracking and task management integrations in `config/keys.env`, then run this action manually or schedule it via launchd (macOS) or cron.

## Task

1. Pull time entries from the previous calendar week from your time tracker (Toggl, Harvest, etc.).
2. Group entries by project or category.
3. Pull upcoming tasks from your task manager (Asana, Linear, etc.).
4. Write a weekly check-in summary to `convos/weekly-check-ins/YYMMDD-week.md`.

Customise the categories and integrations to match your workflow.
