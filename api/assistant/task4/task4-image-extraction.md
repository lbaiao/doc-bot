The current approach to image extraction is not working as expected.

The current approach relies on taking PDF pages screenshots and cutting images out of them, assisted by an orienting grid and a LLM. Please review the project, so you can understand this algorithm better.

This approach leads us to:
- Cutting images on the wrong places
- Missing images that are not well oriented in the PDF pages
- Extracting inappropriate pieces of the pages as images

We need to come up with a better approach to this. I need to you plan and come up with new strategies.

You can find an example of a bad cut image at ./bad-cut-image.png
