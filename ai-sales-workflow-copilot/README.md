# AI Sales Workflow Copilot

A local-first Python AI sales workflow agent built with Ollama, Gmail API, and Google Calendar API. It triages due leads, prioritises next actions, prepares grounded follow-up drafts, tracks outcomes, and optionally schedules meetings—with human approval for external actions.

## Features

- Local product Q&A with Ollama (`llama3.2:3b` by default)
- Product-grounded answers that avoid inventing integrations, guarantees, or results
- Calculator tool with deterministic validation
- Lead capture, duplicate-email checks, search, and listing
- Transparent heuristic lead priority (High / Medium / Low; not a sales prediction)
- Sales dashboard with pipeline counts, due/overdue follow-ups, and next-action suggestions
- Follow-up queue ordered by due date and priority
- Lead status and follow-up date updates
- Gmail email drafts with preview and explicit confirmation before sending
- Google Calendar appointment creation
- End-to-end follow-up flow: select lead → review/send email → optionally book a meeting
- Multi-lead `sales automation` run: triage due leads, rank them by due date and transparent priority, prepare personalised drafts, update lead status after confirmed sends, and optionally book meetings
- Human-in-the-loop safeguards: no email is sent and no meeting is booked without explicit confirmation
- Local JSON storage for leads and agent state

## Requirements

- Python 3.10+
- [Ollama](https://ollama.com/) installed and running
- A pulled model, for example `ollama pull llama3.2:3b`
- Google Cloud OAuth desktop credentials with Gmail API and Google Calendar API enabled

## Setup (Windows PowerShell)

1. Open this folder in VS Code or PowerShell.
2. Create and activate a virtual environment:

   ```powershell
   py -3.10 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Start Ollama and pull the model:

   ```powershell
   ollama pull llama3.2:3b
   ollama serve
   ```

   If Ollama is already running in the background, you do not need to start it again.

5. Place your Google OAuth `credentials.json` in the project folder. On first Gmail/Calendar use, the program opens a browser for authorization and stores `token.json` locally.
6. Run:

   ```powershell
   python sales_agent_unified_v6.py
   ```

## Commands

| Command | Purpose |
|---|---|
| `add lead` | Capture a lead interactively |
| `list leads` | View saved leads, status, priority, and follow-up date |
| `search leads <term>` | Search saved leads |
| `sales dashboard` | Summarise the pipeline and due/overdue follow-ups |
| `follow-up queue` | Show open leads needing attention |
| `update lead status <ID> <status>` | Set status: New, Contacted, Qualified, Meeting Scheduled, Won, Lost, or Closed |
| `set follow-up <ID> YYYY-MM-DD` | Set a lead's follow-up date |
| `follow up lead` | Run a reviewed email follow-up for one selected lead and optionally book a meeting |
| `sales automation` | Triage due leads and process reviewed follow-ups one at a time |
| `email lead` | Choose a saved lead and prepare an email |
| `calculate 5 x 200` | Calculate a total |
| `memory` | View conversation history |
| `clear memory` | Clear conversation history and the previous draft |
| `exit` | Quit the program |

New leads default to status `New` and a follow-up date of tomorrow. After a follow-up email is successfully sent through the guided workflow, the lead is marked `Contacted` and a suggested follow-up date is set three days later. The dashboard is an on-demand report. The `sales automation` command is an interactive batch workflow, not a background scheduler: it asks before processing each lead and requires email approval before sending. It does not send unattended emails.

## Safety and privacy

- Email sending requires a preview and explicit confirmation.
- Calendar actions are interactive; do not assume a meeting exists unless the app confirms success.
- Product answers use the product facts defined in the source code. Add verified product information before relying on answers about features or integrations.
- Lead priority is a simple transparent heuristic, not an AI prediction or guarantee of conversion.
- OAuth credentials, tokens, lead records, conversation memory, and agent state are local files and must not be committed to GitHub.

## GitHub preparation

Review `.gitignore` before committing. Do not commit `credentials.json`, `token.json`, `.env`, or personal lead/memory/state JSON files. Use a clean demo dataset if you want screenshots or a demo recording.

## Testing

Run the smoke tests after installing dependencies:

```powershell
python -m unittest discover -s tests -v
```

The current implementation is a local prototype. It is not connected to a production CRM and does not provide unattended background scheduling. Lead priority is a transparent heuristic, not an ML-based conversion prediction.
