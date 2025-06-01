import type { Sentence } from '../types';

const VIDEO_WIDTH = 1280;
const VIDEO_HEIGHT = 720;
const VIDEO_FPS = 25; // Standard video frame rate
const TRANSITION_DURATION = 0.5; // seconds
const DEFAULT_BG_COLOR = '#1E293B'; // slate-800
const TEXT_COLOR = '#FFFFFF';
const TEXT_BG_COLOR = 'rgba(0, 0, 0, 0.6)';
const FONT_SIZE = 40; // px
const FONT_FAMILY = 'Arial, sans-serif';
const TEXT_PADDING = 10; // px
const TEXT_MARGIN_BOTTOM = 60; // px from bottom of video

async function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous'; // Important for canvas if images are from different origins
    img.onload = () => resolve(img);
    img.onerror = (err) => reject(new Error(`Failed to load image: ${url}. ${err}`));
    img.src = url;
  });
}

function drawScene(
  ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D,
  canvasWidth: number,
  canvasHeight: number,
  sentence: Sentence,
  image: HTMLImageElement | null
) {
  // Clear canvas / Draw background
  ctx.fillStyle = DEFAULT_BG_COLOR;
  ctx.fillRect(0, 0, canvasWidth, canvasHeight);

  // Draw image
  if (image) {
    const aspectRatio = image.naturalWidth / image.naturalHeight;
    let drawWidth = canvasWidth;
    let drawHeight = drawWidth / aspectRatio;

    if (drawHeight > canvasHeight) {
      drawHeight = canvasHeight;
      drawWidth = drawHeight * aspectRatio;
    }

    const x = (canvasWidth - drawWidth) / 2;
    const y = (canvasHeight - drawHeight) / 2;
    ctx.drawImage(image, x, y, drawWidth, drawHeight);
  } else {
    // Optional: Draw a placeholder visual if no image
    ctx.fillStyle = 'rgba(255,255,255,0.1)';
    ctx.fillRect(canvasWidth * 0.25, canvasHeight * 0.25, canvasWidth * 0.5, canvasHeight * 0.5);
    ctx.fillStyle = TEXT_COLOR;
    ctx.textAlign = 'center';
    ctx.font = `italic ${FONT_SIZE*0.6}px ${FONT_FAMILY}`;
    ctx.fillText("No image generated", canvasWidth / 2, canvasHeight / 2);
  }

  // Draw text
  ctx.font = `${FONT_SIZE}px ${FONT_FAMILY}`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';

  const lines = wrapText(ctx, sentence.text, canvasWidth - TEXT_PADDING * 4); // Max width for text
  const lineHeight = FONT_SIZE * 1.2;
  const totalTextHeight = lines.length * lineHeight;
  
  let startY = canvasHeight - TEXT_MARGIN_BOTTOM - totalTextHeight + lineHeight - (TEXT_PADDING / 2) ;

  // Draw text background
  if (lines.length > 0) {

    ctx.fillStyle = TEXT_BG_COLOR;
    // Calculate background box based on longest line
    // ctx.fillRect(bgX, bgY, bgWidth, bgHeight); // Rect for all lines
     // Draw background for each line separately if text alignment is center
     lines.forEach((line, index) => {
      const lineWidth = ctx.measureText(line).width;
      const lineBgX = (canvasWidth - (lineWidth + TEXT_PADDING * 2)) / 2;
      const lineBgY = startY + (index * lineHeight) - lineHeight - TEXT_PADDING;
      const lineBgWidth = lineWidth + TEXT_PADDING * 2;
      const lineBgHeight = lineHeight + TEXT_PADDING;
       if(line.trim()){
         ctx.fillRect(lineBgX, lineBgY, lineBgWidth, lineBgHeight);
       }
    });
  }


  // Draw text lines
  ctx.fillStyle = TEXT_COLOR;
  lines.forEach((line, index) => {
    ctx.fillText(line, canvasWidth / 2, startY + index * lineHeight);
  });
}

// Helper to wrap text for canvas
function wrapText(context: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D, text: string, maxWidth: number): string[] {
    const words = text.split(' ');
    const lines: string[] = [];
    let currentLine = words[0];

    for (let i = 1; i < words.length; i++) {
        const word = words[i];
        const width = context.measureText(currentLine + " " + word).width;
        if (width < maxWidth) {
            currentLine += " " + word;
        } else {
            lines.push(currentLine);
            currentLine = word;
        }
    }
    lines.push(currentLine);
    return lines;
}


export async function createVideoFromSentences(
  sentences: Sentence[],
  backgroundMusicUrl: string | null = null // New parameter for background music
): Promise<string> {
  return new Promise(async (resolve, reject) => {
    if (!sentences || sentences.length === 0) {
      return reject(new Error("No sentences provided for video generation."));
    }

    // --- Audio Context for Background Music (Simulated) ---
    let audioContext: AudioContext | null = null;
    let backgroundMusicAudio: HTMLAudioElement | null = null;

    if (backgroundMusicUrl) {
      try {
        audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        backgroundMusicAudio = new Audio(backgroundMusicUrl);
        backgroundMusicAudio.loop = true; // Loop background music
        backgroundMusicAudio.volume = 0.5; // Initial volume

        // Connect audio to context (for playback, not for recording into MediaRecorder directly)
        // For actual recording, you'd need a MediaStreamDestinationNode and merge tracks.
        // This is a simplification for simulation.
        const source = audioContext.createMediaElementSource(backgroundMusicAudio);
        source.connect(audioContext.destination);
        backgroundMusicAudio.play().catch(e => console.warn("Failed to play background music:", e));
      } catch (e) {
        console.warn("Could not initialize AudioContext or load background music:", e);
        backgroundMusicAudio = null; // Disable background music if there's an error
      }
    }

    // Use OffscreenCanvas if available, otherwise fallback to regular canvas
    let canvas: HTMLCanvasElement | OffscreenCanvas;
    let ctx: CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D | null;

    if (typeof OffscreenCanvas !== 'undefined') {
        canvas = new OffscreenCanvas(VIDEO_WIDTH, VIDEO_HEIGHT);
    } else {
        canvas = document.createElement('canvas');
        canvas.width = VIDEO_WIDTH;
        canvas.height = VIDEO_HEIGHT;
        // Optionally append to body for debugging: document.body.appendChild(canvas);
    }
    
    ctx = canvas.getContext('2d', { alpha: false }) as CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;
    if (!ctx) {
        return reject(new Error("Failed to get canvas context."));
    }


   // @ts-ignore MediaRecorder might not be fully typed for OffscreenCanvas stream
   const stream = canvas.captureStream(VIDEO_FPS);
   if (!stream) {
     return reject(new Error("Failed to capture stream from canvas."));
   }

   // In a real scenario, if we had audio from speech generation, we'd merge it here:
   // const audioStream = await getSpeechAudioStream(sentences); // Hypothetical function
   // const combinedStream = new MediaStream([...stream.getVideoTracks(), ...audioStream.getAudioTracks()]);
   // const recorder = new MediaRecorder(combinedStream, { mimeType: supportedMimeType });
    
    const mimeTypes = [
        'video/webm;codecs=vp9,opus',
        'video/webm;codecs=vp9',
        'video/webm;codecs=vp8,opus',
        'video/webm;codecs=vp8',
        'video/mp4;codecs=h264', // Less likely to be supported by MediaRecorder directly for canvas
        'video/webm'
    ];
    const supportedMimeType = mimeTypes.find(type => MediaRecorder.isTypeSupported(type));

    if (!supportedMimeType) {
        return reject(new Error("No suitable MIME type found for MediaRecorder. WebM (VP8/VP9) is preferred."));
    }
    
    const recorder = new MediaRecorder(stream, { mimeType: supportedMimeType });
    const chunks: Blob[] = [];

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(chunks, { type: supportedMimeType });
      const videoUrl = URL.createObjectURL(blob);
      // if using a visible canvas for debugging, remove it: if (canvas instanceof HTMLCanvasElement && canvas.parentElement) canvas.remove();
      resolve(videoUrl);
    };

    recorder.onerror = (event) => {
      // if using a visible canvas for debugging, remove it: if (canvas instanceof HTMLCanvasElement && canvas.parentElement) canvas.remove();
      reject(new Error(`MediaRecorder error: ${ (event as any)?.error?.name || 'Unknown error' }`));
    };

    recorder.start();

    try {
      for (let i = 0; i < sentences.length; i++) {
        const sentence = sentences[i];
        let currentImage: HTMLImageElement | null = null;

        if (sentence.imageUrl) {
          try {
            currentImage = await loadImage(sentence.imageUrl);
          } catch (imgError) {
            console.warn(`Could not load image for sentence "${sentence.text.substring(0,20)}...": ${(imgError as Error).message}`);
            // Continue without image for this scene
          }
        }

        // Calculate effective duration for the current scene, accounting for transition
        const sceneDuration = sentence.endTime - sentence.startTime;
        const framesForScene = Math.max(1, Math.round(sceneDuration * VIDEO_FPS));
        const transitionFrames = Math.round(TRANSITION_DURATION * VIDEO_FPS);

        // Draw current scene for its duration
        for (let frame = 0; frame < framesForScene; frame++) {
          drawScene(ctx, canvas.width, canvas.height, sentence, currentImage);
          await new Promise(r => setTimeout(r, 1000 / VIDEO_FPS));
        }

        // Handle transition to the next scene if it exists
        if (i < sentences.length - 1) {
          const nextSentence = sentences[i + 1];
          let nextImage: HTMLImageElement | null = null;
          if (nextSentence.imageUrl) {
            try {
              nextImage = await loadImage(nextSentence.imageUrl);
            } catch (imgError) {
              console.warn(`Could not load next image for transition: ${(imgError as Error).message}`);
            }
          }

          for (let frame = 0; frame < transitionFrames; frame++) {
            const progress = frame / transitionFrames; // 0 to 1
            
            // Draw previous scene (current sentence's image)
            drawScene(ctx, canvas.width, canvas.height, sentence, currentImage);

            // Overlay next scene with increasing opacity
            ctx.globalAlpha = progress;
            drawScene(ctx, canvas.width, canvas.height, nextSentence, nextImage);
            ctx.globalAlpha = 1; // Reset for next draws

            await new Promise(r => setTimeout(r, 1000 / VIDEO_FPS));
          }
        }
        previousImage = currentImage; // Store current image for potential future transitions
      }
    } catch (error) {
      if (recorder.state === 'recording') {
        recorder.stop(); // Ensure recorder is stopped on error
      }
      // if using a visible canvas for debugging, remove it: if (canvas instanceof HTMLCanvasElement && canvas.parentElement) canvas.remove();
      return reject(error); // Propagate error
    }

    if (recorder.state === 'recording') {
      recorder.stop();
    }
    if (backgroundMusicAudio) {
      backgroundMusicAudio.pause();
      backgroundMusicAudio.currentTime = 0;
    }
    if (audioContext) {
      audioContext.close();
    }
  });
}
