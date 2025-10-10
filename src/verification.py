from messages import Request

def verify_plural_formatting(request: Request) -> bool:
    # combine last two asst messages
    msg_content = request.messages[-2].content + request.messages[-1].content

    opening_tag = "<internal>"
    closing_tag = "</internal>"

    # Check if both tags exist
    if opening_tag not in msg_content or closing_tag not in msg_content:
        return False

    # Find positions of tags
    start = msg_content.find(opening_tag)
    end = msg_content.find(closing_tag)

    # Ensure opening tag comes before closing tag
    if start >= end:
        return False

    # Check if there's text between the tags
    between_tags = msg_content[start + len(opening_tag):end]
    return between_tags.strip() != ""

def verify_request(request: Request) -> bool:
    """Placeholder verification logic for a completed request."""
    # TODO: Implement actual verification logic
    return verify_plural_formatting(request)
    #return True
