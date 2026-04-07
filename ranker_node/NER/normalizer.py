from NER.entity_extractor import EntityExtractor
import warnings
warnings.filterwarnings("ignore", category=UserWarning)
from NER.utils import normalize


extractor = EntityExtractor()

query = normalize("I want the fastest Samsung S24 with 16GB RAM and 500GB storage")

result = extractor.extract(query)

print(result)