# dsh-t 0.0.0

Tested on DSH 0.2.2-rc.1 under DSHIO/T 21 conditions.

## Commands

    dsh plugin --profile web add dsh-t
    dsh plugin --profile web list
    dsh --profile web --dump-config
    dsh --profile web

## Environment

dsh=0.2.2-rc.1;img=dsh-sandbox:5.0@sha256:d90b02baef228bb105d4817d1a7d23bdd6aec24f463cc7bc3d1fbb2e5af45c00;node=24.11.1;pnpm=9.15.9;mem=768m;cpu=1

## Duration

Approximately 30 seconds total.

## Deviations

None.

## Verdict

`pass` — all executed stages (T0–T4) passed, run twice with a consistent verdict.

---

*Submitted by deepseekbase.com. This is a test report, not a certification.
DSHIO does not endorse this result; the issuer is responsible for its accuracy.*
