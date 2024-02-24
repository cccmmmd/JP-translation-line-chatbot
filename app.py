import sys
import configparser

#Azure Translation
from azure.ai.translation.text import TextTranslationClient, TranslatorCredential
from azure.ai.translation.text.models import InputTextItem
from azure.core.exceptions import HttpResponseError

from flask import Flask, request, abort
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

#Config Parser
config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__)

channel_access_token = config['Line']['CHANNEL_ACCESS_TOKEN']
channel_secret = config['Line']['CHANNEL_SECRET']
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

handler = WebhookHandler(channel_secret)

configuration = Configuration(
    access_token=channel_access_token
)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    returnMessages = []
    translation_result = azure_translate(event.message.text)

    for res in translation_result:
        returnMessages.append(TextMessage(text=f"{res}"))

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=returnMessages
            )
        )

def azure_translate(user_input):

    credential = TranslatorCredential(config['AzureTranslator']["Key"], config['AzureTranslator']["Region"])
    text_translator = TextTranslationClient(endpoint=config['AzureTranslator']["EndPoint"], credential=credential)

    try:
        target_languages = ["ja","en","zh-Hant"]
        input_text_elements = [ InputTextItem(text = user_input) ]

        response = text_translator.translate(content = input_text_elements, to = target_languages)
        # print(response)
        translation = response[0] if response else None

        if translation:
          ## jp -> tw, en
            if translation['detectedLanguage']['language'] == "ja":
                return [translation.translations[1].text, translation.translations[2].text]
            else:
                return [translation.translations[0].text]

        # return translation.translations[0].text

    except HttpResponseError as exception:
        print(f"Error Code: {exception.error}")
        print(f"Message: {exception.error.message}")

if __name__ == "__main__":
    app.run()