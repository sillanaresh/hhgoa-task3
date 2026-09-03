# Test plan

## Automated checks

Run:

```bash
./scripts/check.sh
```

This covers source formatting, lint, strict typing, tests with coverage, common Python security issues, and known dependency vulnerabilities.

The deterministic integration test replaces the external search and public network with controlled service doubles. It runs the same production pipeline from image decode through evidence preparation, publication, verification, idempotent repeat publication, and tamper failure.

## Required live checks

These checks use real external systems and are performed before the recording.

| Check | Expected result |
|---|---|
| Clear public figure image | One or more faces found, largest selected, 128 dimension embedding reported |
| Image with no face | Run stops at face stage with clear recovery text |
| Live crop and full image search | Two search traces with new provider IDs when supplied |
| Public social result | Original post opens and contains the matching person |
| Candidate comparison | At least one candidate passes the visible threshold |
| Evidence download | Downloaded JSON hashes to the displayed fingerprint |
| Public write | One zero value Base Sepolia self transaction confirms |
| Repeat verification | Saved evidence passes against the same transaction |
| Tampered evidence copy | Standalone verification exits with failure |
| Missing test ETH | Publication stops without claiming verification and preserves evidence |

## Browser and accessibility checks

Test desktop widths at 1440 and 1024 pixels. Test mobile widths at 768, 414, 375, and 320 pixels.

- No horizontal scrolling.
- Every control is reachable by keyboard.
- Focus is visible.
- Form controls have labels and required state.
- Status changes are announced through polite live regions.
- Color is not the only status indicator.
- Buttons remain at least 44 pixels high.
- Text remains readable at 200 percent zoom.
- Reduced motion removes the active pulse and smooth transitions.
- Long source titles, hashes, and transaction IDs do not force overflow.
- Failed runs keep completed work and show one clear recovery action.

## Final submission gate

Do not submit until all automated checks pass, the real end to end run verifies, the public repository contains no secret, and both submission links work in a private browser window.
