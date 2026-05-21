from apps.notes.models.note import Note


def create_note(user_id: int, text: str) -> Note:
    """Create a new note for the user."""
    return Note.objects.create(user_id=user_id, text=text)


def delete_note(note_id: int, user_id: int) -> None:
    """Delete a note owned by the user."""
    Note.objects.filter(id=note_id, user_id=user_id).delete()


def pin_note(note_id: int, user_id: int) -> Note:
    """Toggle pin status on a note."""
    note = Note.objects.get(id=note_id, user_id=user_id)
    note.is_pinned = not note.is_pinned
    note.save(update_fields=["is_pinned", "updated_at"])
    return note


def update_note(note_id: int, user_id: int, text: str) -> Note:
    """Update the text of an existing note."""
    note = Note.objects.get(id=note_id, user_id=user_id)
    note.text = text
    note.save(update_fields=["text", "updated_at"])
    return note
