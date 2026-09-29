import requests


class WebSearch:
    def search(self, query: str, max_results: int = 5):
        url = "https://api.duckduckgo.com/?q=" + requests.utils.quote(query) + "&format=json&no_redirect=1&no_html=1"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            payload = response.json()

            results = []
            for item in payload.get("RelatedTopics", [])[:max_results]:
                if isinstance(item, dict):
                    results.append(
                        {
                            "title": item.get("Text", item.get("Name", "Result")),
                            "url": item.get("FirstURL", "https://duckduckgo.com"),
                            "snippet": item.get("Text", ""),
                        }
                    )
                elif isinstance(item, str):
                    results.append({"title": item, "url": "https://duckduckgo.com", "snippet": item})

            if results:
                return results

            abstract = payload.get("AbstractText")
            if abstract:
                return [{"title": payload.get("Heading", query), "url": payload.get("AbstractURL", "https://duckduckgo.com"), "snippet": abstract}]

            return [{"title": query, "url": "https://duckduckgo.com", "snippet": "No live search results returned."}]
        except Exception:
            return [{"title": query, "url": "https://duckduckgo.com", "snippet": "Live search is unavailable right now, but I can still help with local tasks and project work."}]
