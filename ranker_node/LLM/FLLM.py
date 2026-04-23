import os
from importlib import import_module
from typing import List

genai = import_module("google.genai")

class MarkdownDescription:
    def __init__(self, products: List[dict]) -> None:
        self.products = products
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.gemini_key) if self.gemini_key else None

    def _format_products(self) -> str:
        products_text = ""
        for i, product in enumerate(self.products):
            description = product.get("description", "No description provided")
            price = product.get("price", "N/A")
            products_text += f"""
            Product {i+1}:
            - Original description: {description}
            - Price: ${price}
            """
        return products_text

    def _fallback_markdown(self) -> str:
        sections = [
            "Happy to help! Here are the winners based on what you told me.",
            "",
        ]
        for i, product in enumerate(self.products, 1):
            name = product.get("name") or product.get("title") or f"Product {i}"
            description = product.get("description", "No description provided")
            price = product.get("price", "N/A")
            sections.extend([
                f"## Rank {i} – {name}",
                f"*Price:* ${price}",
                f"*Description:* {description}",
                "",
            ])
        return "\n".join(sections).strip()

    def _normalize_output_format(self, generated_text: str) -> str:
        text = (generated_text or "").strip()
        if not text:
            return self._fallback_markdown()

        if "| Rank |" not in text:
            return text

        return self._fallback_markdown()

    def generate(self) -> str:
        """Generate a markdown description for the 5 products."""
        products_text = self._format_products()
        prompt = f"""
You are an expert e‑commerce copywriter and product analyst.  
You are given 5 products, each with an original description and a price.

Your task is:

1. *Write a short, friendly, human‑like opening sentence* (like a helpful sales assistant) that acknowledges the user's request.  
    You can use one of these exactly, or create something very similar in tone:
    - "Oh, nice choice! Here's what I found that matches your vibe."
    - "Love this request – let me hook you up with the best ones."
    - "You've got great taste! Check out these top picks."
    - "I'm excited to show you these – they're exactly what you're looking for."
    - "Happy to help! Here are the winners based on what you told me."
    - "Alright, I did some digging – and here's the cream of the crop."
    - "You're going to like these – I've ranked them from awesome to still pretty good."
    - "Boom! Here's your personalized ranking – hope it makes your decision easier."
    - "I've got your back! Check out these hand‑ranked picks."
    - "Ta‑da! Here's your custom‑ranked list – enjoy the hunt."

2. *For each product, write a concise, specific, and compelling description* as a single paragraph (30–60 words).  
    - Highlight key features, use cases, and value.  
    - If the original description is poor, improve it. Keep factual and search‑friendly.

3. *Rank the 5 products from best (rank 1) to worst (rank 5)* based on *both*:
    - Quality of your new description (clarity, completeness, relevance).
    - Price (lower is better, unless higher price brings significantly better features).

4. *Output ONLY the opening sentence + the markdown product list* – no extra commentary.  
    Use this structure:

[Opening sentence]

## Rank X – [Product Name or "Product X"]
*Price:* $...
*Description:* (one paragraph, no bullet points)

... up to rank 5.

Rules:
- Do not include any "Why this rank" or justification line.
- If a product has no name, use "Product 1", "Product 2", etc.
- Be realistic with prices and features.

Here are the 5 products:

{products_text}

Now produce only the output (opening sentence + markdown list).
"""
        if not self.client:
            return self._fallback_markdown()

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return self._normalize_output_format(response.text or "")
        except Exception as e:
            print(f"[FLLM ERROR] {e}")
            return self._fallback_markdown()
