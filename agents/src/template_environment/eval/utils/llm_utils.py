import re
import math

def logprob_to_confidence(logprob, base='e'):
    if base == 'e':  # natural log
        return math.exp(logprob)
    elif base == '10':  # base-10 log
        return 10 ** logprob
    else:
        raise ValueError("Unsupported log base. Use 'e' or '10'.")

def extract_score_confidence(response_dict, fields):
    """
    Extract numeric scores and logprobs from an OpenAI-compatible API response.

    Features:
      - Works regardless of tokenizer (OpenAI, vLLM, etc.)
      - Handles multi-token field names
      - Case-insensitive matching
      - Handles decimals, negative numbers, and scientific notation
      - Ignores extra spaces/quotes
      - Returns average logprob for multi-token numbers

    Args:
        response_dict (dict): Full API JSON response from an OpenAI-compatible API.
        fields (list[str]): List of exact field names to extract.

    Returns:
        dict: {
            field_name: float,
        }
    """
    logprobs_tokens = response_dict["choices"][0]["logprobs"]["content"]
    tokens = [t["token"] for t in logprobs_tokens]
    logprobs = [t["logprob"] for t in logprobs_tokens]

    # Reconstruct full raw string for searching
    raw_output = "".join(tokens)

    scores_with_logprobs = {}

    for field in fields:
        # Case-insensitive search
        search_pattern = re.compile(re.escape(field), re.IGNORECASE)

        for match in search_pattern.finditer(raw_output):
            char_pos = match.start()

            # Map char position -> token index
            char_count = 0
            matched_tokens = []
            token_index = None
            for i, tok in enumerate(tokens):
                char_count += len(tok)
                if char_count > char_pos:
                    token_index = i
                    matched_tokens.append(tok)
                    if "".join(matched_tokens) == field:
                        break

            if token_index is None:
                continue

            # Look forward for numeric value
            j = token_index + 1
            while j < len(tokens):
                tok_clean = tokens[j]
                if tok_clean.isnumeric():
                    # Gather numeric tokens (including -, ., e, digits)
                    num_tokens = []
                    num_logprobs = []
                    k = j
                    while k < len(tokens):
                        t_clean = tokens[k]
                        if re.match(r"^[0-9eE\.\+\-]+$", t_clean):
                            num_tokens.append(t_clean)
                            num_logprobs.append(logprobs[k])
                            k += 1
                        else:
                            break
                    try:
                        value = float("".join(num_tokens))
                        avg_logprob = sum(num_logprobs) / len(num_logprobs)
                        scores_with_logprobs[field] = {
                            "value": value,
                            "logprob": avg_logprob,
                            "tokens": num_tokens,
                            "token_logprobs": num_logprobs
                        }
                    except ValueError:
                        pass
                    break
                j += 1

    field_confidence = {}
    for field in fields:
        if field not in scores_with_logprobs:
            field_confidence[field] = 0.0
        else:
            field_confidence[field] = logprob_to_confidence(scores_with_logprobs[field]["logprob"])

    return field_confidence