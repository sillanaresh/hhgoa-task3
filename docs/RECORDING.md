# Screen recording guide

Aim for a clear recording of three to five minutes. Record one continuous take. Do not show the search key, wallet file, private key, browser passwords, email, or unrelated tabs.

## Before recording

1. Make the GitHub repository public only after the final secret check.
2. Choose a clear image of a public figure that you have tested once.
3. Confirm that the related social post is still public.
4. Keep enough SerpApi searches for at least two runs. Each normal run uses two searches.
5. Keep a small Base Sepolia test ETH balance in the disposable wallet.
6. Close notifications and unrelated applications.
7. Increase browser zoom only if the transaction hash or score is hard to read.

Run:

```bash
./scripts/preflight.sh
git status --short
```

The readiness table must show the search, models, wallet, network, and test ETH as ready. The quality checks must pass. The Git status output must contain no secret or runtime file.

## Recording order

### 1. Establish the repository

Show the GitHub repository for a few seconds. Point to the README pipeline, Base Sepolia section, test command, and known limitations. Do not spend more than 30 seconds here.

### 2. Start the local app

Run:

```bash
./scripts/demo.sh
```

Show the readiness strip. Say that the image will be sent to the live visual search provider, face comparison happens locally, and only the final evidence fingerprint goes to Base Sepolia.

### 3. Run the live search

1. Choose the prepared face image.
2. Confirm the permission statement.
3. Select `Start live search`.
4. Keep the stage rail visible while it advances.
5. When the result appears, open the candidate disclosure briefly so the recording shows that several live results were evaluated.

Say that the app ran two new searches with cache disabled and then made its own local face comparison.

### 4. Inspect the evidence

Show these items together:

- Input and retrieved candidate image.
- Original public post link.
- Cosine similarity score and decision threshold.
- Evidence fingerprint.

Open the original post in a new tab. Confirm that it is a real public social post and that the matching person appears. Return to FaceProof.

### 5. Publish and verify

Read the approval text, then select `Publish fingerprint`. This is the only public write in the demo.

Wait for both blockchain stages to complete. Show the verified receipt, block number, transaction hash, and confirmation count. Open the public Basescan transaction. Point to the Base Sepolia network and transaction input data.

Return to FaceProof and select `Verify again`. Show the confirmation message.

### 6. Close clearly

End on the completed six stage record. State that the original evidence can be downloaded and checked independently with:

```bash
uv run faceproof verify-file evidence.json 0xTRANSACTION_HASH
```

## After recording

1. Watch the entire file once.
2. Confirm that no secret appeared.
3. Upload it as an unlisted YouTube video, Loom recording, or viewable Google Drive file.
4. Test the link in a private browser window.
5. Put the final GitHub and recording links into the submission form only after both links work without your signed in session.

The submission form does not allow resubmission, so do the private window check before submitting.
