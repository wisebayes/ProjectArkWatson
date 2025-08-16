import os
from dotenv import load_dotenv
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

load_dotenv()

# Pull creds from env and validate early
credentials = {
    "url": os.getenv("WATSONX_URL"),
    "apikey": os.getenv("WATSONX_API_KEY"),
}
project_id = os.getenv("WATSONX_PROJECT_ID")

missing = [k for k, v in {**credentials, "project_id": project_id}.items() if not v]
if missing:
    raise SystemExit(f"Missing required env vars: {', '.join(missing)}")

print("Testing watsonx.ai connection...")

params = {
    GenParams.DECODING_METHOD: "greedy",
    GenParams.MAX_NEW_TOKENS: 100,
    GenParams.TEMPERATURE: 0.1,
}

try:
    model = ModelInference(
        model_id="ibm/granite-3-2-8b-instruct",
        params=params,
        credentials=credentials,
        project_id=project_id,
    )

    prompt = "What is IBM watsonx? Keep it to 3 sentences."
    resp = model.generate_text(prompt)

    # Robust extraction: handle str or dict payloads
    if isinstance(resp, str):
        text = resp
    elif isinstance(resp, dict):
        # Typical SDK shape: {"results": [{"generated_text": "..."}], ...}
        text = (
            resp.get("results", [{}])[0].get("generated_text")
            or resp.get("generated_text")
            or str(resp)
        )
    else:
        text = str(resp)

    print("SUCCESS: watsonx.ai connection working!")
    print("\nResponse:\n")
    print(text)

except Exception as e:
    print(f"ERROR: {e}")
    print("Check your .env values and network access (URL, API key, project id).")