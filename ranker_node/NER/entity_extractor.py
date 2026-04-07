from gliner import GLiNER  # type: ignore

class EntityExtractor:
    def __init__(self):
        # Load model once (using a smaller model to avoid a 1.5GB download)
        self.model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")

        # Define YOUR schema (this is the power of GLiNER)
        self.labels = [
        "brand (company or manufacturer like Samsung, Apple, HP)",
        "model (product model like S24, iPhone 15, Pavilion)",
        "spec (technical specifications like 16GB, 500GB, RTX 3060, PLA, 780M)",
        "intent (user intent words like want, looking for, fastest, cheapest)",
        "price (amount of money, budget, cost like $500, under 1000, 50 dollars)"
        ]

    def extract(self, text: str):
        entities = self.model.predict_entities(text, self.labels)
        filtered = [e for e in entities if e["score"] > 0.5]
        return self._format_entities(filtered)

    def _format_entities(self, entities):
        result = {
            "brand": set(),
            "model": set(),
            "spec": set(),
            "intent": set(),
            "price": set()
        }

        for ent in entities:
            # The label returned by GLiNER might be the full string. We only want the first word ("brand", "model", etc.)
            label = ent["label"].split(" ")[0]
            
            # If the label somehow isn't in our result dictionary, ignore it to prevent KeyError
            if label not in result:
                continue
                
            value = ent["text"].lower()
            result[label].add(value)

        # convert back to list
        return {k: list(v) for k, v in result.items()}