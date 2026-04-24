import os
from importlib import import_module
from typing import List

genai = import_module("google.genai")
from core.sanitization import sanitize_text, sanitize_html  # type: ignore[import-not-found]

class MarkdownDescription:
    def __init__(self, products: List[dict], intent: str = "search") -> None:
        self.products = products
        self.intent = intent
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
            name = sanitize_text(product.get("name") or product.get("title") or f"Product {i}", 100)
            description = sanitize_text(product.get("description", "No description provided"), 500)
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

        # Sanitize the generated text to prevent XSS
        text = sanitize_html(text, 10000)

        if "| Rank |" not in text:
            return text

        return self._fallback_markdown()

    def generate(self) -> str:
        """Generate a markdown description for the products based on intent."""
        if self.intent == "comparison":
            return self._generate_comparison_table()
        elif self.intent == "constrained":
            return self._generate_constrained_list()
        else:
            return self._generate_standard_list()

    def _generate_standard_list(self) -> str:
        """Generate standard ranked list."""
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

    def _generate_comparison_table(self) -> str:
        """Generate comparison table for comparison intent."""
        if not self.products:
            return "No products to compare."
        
        # Create a markdown table
        header = "| Feature | " + " | ".join([f"Product {i+1}" for i in range(len(self.products))]) + " |"
        separator = "|" + "|".join(["---"] * (len(self.products) + 1)) + "|"
        
        rows = []
        # Price row
        price_row = "| Price | " + " | ".join([f"${p.get('price', 'N/A')}" for p in self.products]) + " |"
        rows.append(price_row)
        
        # Description row (truncated)
        desc_row = "| Description | " + " | ".join([p.get('description', 'N/A')[:50] + "..." for p in self.products]) + " |"
        rows.append(desc_row)
        
        table = "\n".join([header, separator] + rows)
        return f"Here's a comparison of the top products:\n\n{table}"

    def _generate_constrained_list(self) -> str:
        """Generate short constrained list."""
        if not self.products:
            return "No products found matching your constraints."
        
        lines = ["Here are the top products that match your specific requirements:"]
        for i, product in enumerate(self.products, 1):
            desc = product.get('description', 'No description')[:100]
            price = product.get('price', 'N/A')
            lines.append(f"{i}. {desc} - ${price}")
        return "\n".join(lines)
