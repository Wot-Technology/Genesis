import json


class Prompts:
    @staticmethod
    def get_product_correction_prompt() -> str:
        prompt = {
            "instruction": "Correct the product list. Ensure each product name meets the provided standards using descriptions and metadata. Enhance names with specific details (e.g., material strength, type, features). Maintain branded information if 'Branch Intrinsic' is true; otherwise, remove it. Use 'OriginalBrand' if the brand is missing. Include all brands from the 'Brands' field. Ensure the code is in the title. Ignore missing fields, BMSKU, and 'BS EN'. Return only 'BM Product' as JSON for each provided product.",
            # "instruction": "Correct the following product list and ensure that each product name "
            #                "meets the standard provided for the field in the standards section."
            #                "Use the provided descriptions and meta to improve the corrections."
            #                "Use your knowledge of the product to include any specific details that would enhance the "
            #                "name of the product, such as material strength ratings, material type, special features, etc. "
            #                "In the metadata, you will see fields such as Branch Intrinsic, which means it's important to maintain any branded information if true, or false to remove it. "
            #                "If the brand is missing, and OriginalBrand is present then use that. If the meta includes a Brands field, then use every brand in that."
            #                "If code is present, ensure it is in the title. If content requested is missing, ingore that field. Ignore BMSKU and 'BS EN' as it is not key information."
            #                "Only return BM Product as JSON as the output. Do not include any other fields.",
            "standards": {
                "BM Product": "Must include the original item name, any meta Brands available, dimensions, key materials, any product key information such as code or particular properties of interest, and a pack quantity in that order. Use - to seperate each element.",
            }
        }

        return json.dumps(prompt, indent=4)
