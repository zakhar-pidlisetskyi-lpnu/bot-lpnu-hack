import mongoengine as me


class Question(me.EmbeddedDocument):
    name = me.StringField(required=True)
    message = me.StringField(required=True)
    # photo = me.StringField(default=None)
    buttons = me.ListField(default=list())
    input_type = me.StringField(
        choices=["text", "photo", "contact", "document"], default="text"
    )
    max_text_size = me.IntField(max_value=4000)
    allow_user_input = me.BooleanField(default=True)
    regex = me.StringField(default=None)
    correct_answer_message = me.StringField(defaul=None)
    wrong_answer_message = me.StringField(default="Неправильний формат!")


class Quiz(me.Document):
    name = me.StringField(required=True)
    questions = me.ListField(me.EmbeddedDocumentField(Question), default=list())
    is_required = me.BooleanField(default=False)
