import { GoogleGenAI } from "@google/genai";
import { MODEL_IMAGE_GEN, MODEL_TTS_GEN } from '../types';

// WARNING: Hardcoding API keys is not recommended for production applications.
const API_KEY = "AIzaSyCHBXWyH9tiTNAN8fCryYAIN29qguzkhQk";

if (!API_KEY) {
  // This check is more of a safeguard for the developer during refactoring,
  // as the key is hardcoded above.
  console.error("API_KEY is not set in geminiService.ts. This is a critical error.");
  // alert("Critical Error: Gemini API Key is not configured in the application code.");
}

export async function generateImageFromText(prompt: string): Promise<string> {
  if (!API_KEY) {
    // This error will now primarily be caught by the console error above,
    // but kept here for robustness in case the top constant is accidentally cleared.
    throw new Error("Gemini API key is not configured in the application code.");
  }
  const ai = new GoogleGenAI({ apiKey: API_KEY });

  try {
    const response = await ai.models.generateImages({
      model: MODEL_IMAGE_GEN,
      prompt: prompt,
      config: { numberOfImages: 1, outputMimeType: 'image/jpeg' },
    });

    if (response.generatedImages && response.generatedImages.length > 0 && response.generatedImages[0].image.imageBytes) {
      const base64ImageBytes: string = response.generatedImages[0].image.imageBytes;
      return `data:image/jpeg;base64,${base64ImageBytes}`;
    } else {
      throw new Error("No image generated or image data is missing.");
    }
  } catch (error) {
    console.error("Gemini API error (generateImageFromText):", error);
    if (error instanceof Error) {
      if (error.message.includes("API key not valid") || error.message.includes("permission denied")) {
        throw new Error("Invalid or incorrectly configured Gemini API Key. Please verify the hardcoded key.");
      }
      throw new Error(`Failed to generate image: ${error.message}`);
    }
    throw new Error("An unknown error occurred while generating the image.");
  }
}

import mime from 'mime';

export async function generateSpeechFromText(text: string): Promise<string> {
  if (!API_KEY) {
    throw new Error("Gemini API key is not configured in the application code.");
  }
  const ai = new GoogleGenAI({ apiKey: API_KEY });

  const config = {
    temperature: 1,
    responseModalities: ['audio'],
    speechConfig: {
      multiSpeakerVoiceConfig: {
        speakerVoiceConfigs: [
          {
            speaker: 'Speaker 1',
            voiceConfig: {
              prebuiltVoiceConfig: {
                voiceName: 'Zephyr'
              }
            }
          },
          {
            speaker: 'Speaker 2',
            voiceConfig: {
              prebuiltVoiceConfig: {
                voiceName: 'Puck'
              }
            }
          },
        ]
      },
    },
  };
  const model = 'gemini-2.5-flash-preview-tts'; // Use the model specified in the user's code

  const contents = [
    {
      role: 'user' as const,
      parts: [
        {
          text: text,
        },
      ],
    },
  ];

  try {
    const responseStream = await ai.models.generateContentStream({
      model,
      config,
      contents,
    });

    let audioContent: { mimeType: string, data: string } | null = null;

    for await (const chunk of responseStream) {
      if (chunk.candidates && chunk.candidates.length > 0) {
        const candidate = chunk.candidates[0];
        if (candidate.content && candidate.content.parts && candidate.content.parts.length > 0) {
          const part = candidate.content.parts[0];
          if (part && 'inlineData' in part && part.inlineData && part.inlineData.data && part.inlineData.mimeType) {
            audioContent = { mimeType: part.inlineData.mimeType, data: part.inlineData.data };
            break;
          }
        }
      }
    }

    if (audioContent) {
      // The user's provided code had a convertToWav function, but for browser playback,
      // returning a base64 data URL directly is more appropriate.
      // We'll ensure the mime type is correct.
      let fileExtension = mime.getExtension(audioContent.mimeType || '');
      if (!fileExtension) {
        fileExtension = 'wav'; // Default to wav if mime type is unknown
      }
      return `data:${audioContent.mimeType};base64,${audioContent.data}`;
    } else {
      let errorText = "No audio data received from API.";
      const firstChunk = await responseStream.next();
      if (!firstChunk.done && firstChunk.value.text) {
        errorText += ` API responded with text: "${firstChunk.value.text}"`;
      } else {
        errorText += " The response might not contain audio content or the format is unexpected.";
      }
      throw new Error(errorText);
    }

  } catch (error) {
    console.error("Gemini API error (generateSpeechFromText):", error);
    if (error instanceof Error) {
      let errorMessage = error.message;
      try {
        const parsedError = JSON.parse(error.message);
        if (parsedError && parsedError.error && parsedError.error.message) {
          errorMessage = parsedError.error.message;
        }
      } catch (e) {
        // Not a JSON string, use original message
      }

      if (errorMessage.includes("API key not valid") || errorMessage.includes("permission denied")) {
        throw new Error("Invalid or incorrectly configured Gemini API Key. Please verify the hardcoded key.");
      }
      if (errorMessage.toLowerCase().includes("model not found") || errorMessage.toLowerCase().includes("unsupported")) {
        throw new Error(`TTS model '${model}' might be unavailable or unsupported with the current API key. ${errorMessage}`);
      }
      let finalMessage = `Failed to generate speech: ${errorMessage}`;
      if (!finalMessage.includes(error.message) && !error.message.startsWith("Failed to generate speech")) {
         if(error.message !== errorMessage){
            finalMessage += ` (Original SDK error: ${error.message})`;
         }
      }
      throw new Error(finalMessage);
    }
    throw new Error("An unknown error occurred while generating speech.");
  }
}