import os
from dotenv import load_dotenv
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

load_dotenv()

# Test credentials
credentials = {
    'url': os.getenv('WATSONX_URL'),
    'apikey': os.getenv('WATSONX_API_KEY'),
    'project_id': os.getenv('WATSONX_PROJECT_ID')
}

print("Testing watsonx.ai connection...")

try:
    model = Model(
        model_id="ibm/granite-3.2-8b-instruct",
        params={
            GenParams.DECODING_METHOD: "greedy",
            GenParams.MAX_NEW_TOKENS: 100,
            GenParams.TEMPERATURE: 0.1
        },
        credentials=credentials,
        project_id=credentials['project_id']
    )
    
    response = model.generate_text("What is IBM watsonx?")
    print("SUCCESS: watsonx.ai connection working!")
    print(f"Response: {response}")
    
except Exception as e:
    print(f"ERROR: {e}")
    print("Check your credentials in .env file")