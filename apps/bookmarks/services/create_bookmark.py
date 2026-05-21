from apps.bookmarks.models.bookmark import Bookmark


def create_bookmark(user_id: int, label: str, content: str, message_id: int = None) -> Bookmark:
    """Save a message or custom content as a bookmark."""
    return Bookmark.objects.create(
        user_id=user_id,
        label=label,
        content=content,
        message_id=message_id,
    )


def delete_bookmark(bookmark_id: int, user_id: int) -> None:
    """Delete a bookmark owned by the user."""
    Bookmark.objects.filter(id=bookmark_id, user_id=user_id).delete()


def update_bookmark(bookmark_id: int, user_id: int, label: str) -> Bookmark:
    """Update the label of a bookmark."""
    bookmark = Bookmark.objects.get(id=bookmark_id, user_id=user_id)
    bookmark.label = label
    bookmark.save(update_fields=["label", "updated_at"])
    return bookmark
