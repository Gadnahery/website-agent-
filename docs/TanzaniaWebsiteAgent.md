# Tanzania Website Agent Workflow

## Goal

Find Tanzania businesses that:

- have a phone number
- do not have a proper owned website
- look likely to pay for a website

Then generate a brief so you can either:

- cold call them immediately
- or hand the brief to a build agent after they agree

## Workflow

1. Run lead discovery
2. Review the highest-scoring leads
3. Generate proposal briefs for the best ones
4. Export the call sheet
5. Call and update statuses
6. When a lead says yes, mark it as `won` and let the agent generate the build package

## What Counts As "No Website"

The agent keeps leads whose Google Maps profile has:

- no website at all
- only a social profile
- only a marketplace listing like Booking.com or TripAdvisor

## Output Files

- `.mp/website_leads.json`: lead database
- `.mp/call_sheet.csv`: cold-calling export
- `proposals/*.md`: website proposal briefs
- `build-packages/*.md`: won-lead build handoff docs
