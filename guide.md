# Submission Guide

## Requirements

Use Python 3.11 or newer. The default demos do not require an API key.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux or macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run all assignments together

From the repository root:

```powershell
python demo_all.py
```

The combined demo runs all six required scenarios: Assignment 1 clean and failure recovery, Assignment 2 approval and rejection, and Assignment 3 stop/resume and clean processing.

## Run each assignment separately

### Assignment 1

```powershell
cd assignment-1
python demo.py
python research_agent.py --scenario clean
python research_agent.py --scenario failure
```

The failure scenario must show the mocked timeout and then select an independent fallback tool.

### Assignment 2

```powershell
cd ..\assignment-2
python demo.py
python review_chain.py --scenario approve
python review_chain.py --scenario reject
```

The approval scenario should return `approved`. The rejection scenario should return `rejected` with a concrete reason.

### Assignment 3

```powershell
cd ..\assignment-3
python demo.py
python resumable_agent.py --scenario stop-resume
python resumable_agent.py --scenario clean
```

The stop/resume scenario should skip completed items and report the deliberately empty `item4` during self-check.

## Run the complete verification

From the repository root:

```powershell
python smoke_test.py
```

Expected output:

```text
smoke tests passed
```

## Optional live mode

Live mode is optional. Set the environment variables before using it:

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:MODEL="gpt-5-mini"
```

Then run:

```powershell
python demo_all.py --live
```

The live paths use model output where appropriate, but local validation still controls tool names, review approval, checkpoint behavior, and safety limits. If credentials are missing, the applications safely fall back to deterministic behavior.

Never commit an API key to the repository.

## Submission contents

The repository contains three assignment folders. Each folder has source code, a README, dedicated demo runner, and required transcripts. The root contains the dependency file, combined demo runner, smoke tests, and this guide.
