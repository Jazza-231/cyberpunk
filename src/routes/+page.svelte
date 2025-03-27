<script lang="ts">
	// Use window.innerWidth/Height for responsiveness.
	// svelte-ignore non_reactive_update
	let canvasSize = { width: window.innerWidth, height: window.innerHeight };
	const imageSize = { width: 1600, height: 1486 };
	let imageScaledSize = {
		width: canvasSize.width,
		height: Math.floor(imageSize.height / (imageSize.width / canvasSize.width)),
	};

	const levels = 6;

	// Build a 2D array of image paths.
	const levelImages = (() => {
		const images: string[][] = [];
		for (let i = 0; i < levels; i++) {
			images.push([]);
			for (let j = 0; j < 4 ** i; j++) {
				images[i].push(`/levels/${i}/${j}.webp`);
			}
		}
		return images;
	})();

	// Simple image cache.
	const imageCache = new Map<string, HTMLImageElement>();
	function getImage(src: string): HTMLImageElement {
		if (imageCache.has(src)) return imageCache.get(src)!;
		const img = new Image();
		img.src = src;
		imageCache.set(src, img);

		// Ensure image is fully decoded before triggering a redraw.
		img.onload = () => {
			img
				.decode()
				.then(() => {
					drawCanvas(zoom, activeLevel);
				})
				.catch(() => {
					// Fallback if decode() fails.
					drawCanvas(zoom, activeLevel);
				});
		};
		return img;
	}

	// Zoom and pan state.
	let zoom = $state(1);
	let panX = $state((canvasSize.width - imageScaledSize.width) / 2);
	let panY = $state((canvasSize.height - imageScaledSize.height) / 2);

	// activeLevel is the current level being rendered.
	let activeLevel = 0;
	// desiredLevel is computed from zoom.
	let desiredLevel = $derived(Math.min(levels - 1, Math.max(0, Math.floor(Math.log2(zoom)))));

	// When desiredLevel changes, record its timestamp.
	let desiredLevelTimestamp = Date.now();
	$effect(() => {
		desiredLevel;
		desiredLevelTimestamp = Date.now();
	});

	// Returns visible tile indices for a given level, based on current pan/zoom.
	function getVisibleTileIndices(level: number, z: number, panX: number, panY: number): number[] {
		const indices: number[] = [];
		const gridSize = 2 ** level;
		const tileWidth = imageScaledSize.width / gridSize;
		const tileHeight = imageScaledSize.height / gridSize;
		// Compute visible region in map (world) coordinates.
		const xMin = (0 - panX) / z;
		const yMin = (0 - panY) / z;
		const xMax = (canvasSize.width - panX) / z;
		const yMax = (canvasSize.height - panY) / z;
		for (let row = 0; row < gridSize; row++) {
			for (let col = 0; col < gridSize; col++) {
				const tileX0 = col * tileWidth;
				const tileY0 = row * tileHeight;
				const tileX1 = (col + 1) * tileWidth;
				const tileY1 = (row + 1) * tileHeight;
				if (tileX1 < xMin || tileX0 > xMax || tileY1 < yMin || tileY0 > yMax) continue;
				indices.push(row * gridSize + col);
			}
		}
		return indices;
	}

	// Trigger loading of visible images for the desired level.
	$effect(() => {
		const indices = getVisibleTileIndices(desiredLevel, zoom, panX, panY);
		indices.forEach((i) => {
			getImage(levelImages[desiredLevel][i]);
		});
	});

	// Update activeLevel if desired level’s visible images are loaded or if 500ms have passed.
	$effect(() => {
		desiredLevel;
		if (desiredLevel !== activeLevel && allVisibleTilesLoaded(desiredLevel)) {
			activeLevel = desiredLevel;
		} else if (desiredLevel !== activeLevel && Date.now() - desiredLevelTimestamp > 500) {
			activeLevel = desiredLevel;
		}
	});

	function allVisibleTilesLoaded(level: number): boolean {
		const indices = getVisibleTileIndices(level, zoom, panX, panY);
		if (indices.length === 0) return true;
		for (const i of indices) {
			const img = getImage(levelImages[level][i]);
			if (!img.complete) return false;
		}
		return true;
	}

	// Draw a tile using transform: position = (base coordinate × zoom) + pan.
	function drawTile(
		ctx: CanvasRenderingContext2D,
		image: HTMLImageElement,
		i: number,
		level: number,
		z: number,
	) {
		const gridSize = 2 ** level;
		const tileWidth = imageScaledSize.width / gridSize;
		const tileHeight = imageScaledSize.height / gridSize;
		const col = i % gridSize;
		const row = Math.floor(i / gridSize);

		const baseX0 = col * tileWidth;
		const baseX1 = (col + 1) * tileWidth;
		const baseY0 = row * tileHeight;
		const baseY1 = (row + 1) * tileHeight;

		const x0 = baseX0 * z + panX;
		const x1 = baseX1 * z + panX;
		const y0 = baseY0 * z + panY;
		const y1 = baseY1 * z + panY;

		const dx = Math.floor(x0);
		const dy = Math.floor(y0);
		const dWidth = Math.ceil(x1 - x0);
		const dHeight = Math.ceil(y1 - y0);

		ctx.drawImage(image, 0, 0, imageSize.width, imageSize.height, dx, dy, dWidth, dHeight);
		ctx.fillStyle = "white";
		ctx.font = "30px Arial";
		ctx.textBaseline = "top";
		ctx.fillText(i.toString(), dx + 5, dy + 5);
	}

	// Draw the canvas.
	// If at least one tile is loaded (fallback or active) we clear the canvas,
	// otherwise we leave the previous frame to avoid flashing black.
	function drawCanvas(z: number, level: number) {
		const canvas = document.getElementById("canvas") as HTMLCanvasElement;
		if (!canvas) return;
		canvas.width = canvasSize.width;
		canvas.height = canvasSize.height;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;

		let hasLoadedTile = false;

		// Check fallback (one level lower) if available.
		if (level > 0) {
			const fallbackIndices = getVisibleTileIndices(level - 1, z, panX, panY);
			for (const i of fallbackIndices) {
				const img = getImage(levelImages[level - 1][i]);
				if (img.complete) {
					hasLoadedTile = true;
					break;
				}
			}
		}
		// Also check active layer.
		const activeIndices = getVisibleTileIndices(level, z, panX, panY);
		if (!hasLoadedTile) {
			for (const i of activeIndices) {
				const img = getImage(levelImages[level][i]);
				if (img.complete) {
					hasLoadedTile = true;
					break;
				}
			}
		}
		// Only clear if there's at least one loaded tile.
		if (hasLoadedTile) ctx.clearRect(0, 0, canvas.width, canvas.height);

		// Draw fallback first.
		if (level > 0) {
			const fallbackIndices = getVisibleTileIndices(level - 1, z, panX, panY);
			fallbackIndices.forEach((i) => {
				const src = levelImages[level - 1][i];
				const image = getImage(src);
				if (image.complete) {
					drawTile(ctx, image, i, level - 1, z);
				}
			});
		}
		// Then overlay active level.
		activeIndices.forEach((i) => {
			const src = levelImages[level][i];
			const image = getImage(src);
			if (image.complete) {
				drawTile(ctx, image, i, level, z);
			}
		});
	}

	// Redraw when zoom, pan, or activeLevel changes.
	$effect(() => {
		zoom;
		panX;
		panY;
		activeLevel;
		drawCanvas(zoom, activeLevel);
	});

	// --- Momentum & Pointer / Touch Support ---
	let activePointers = new Map<number, { clientX: number; clientY: number }>();
	let isPinching = false;
	let initialPinchDistance = 0;
	// svelte-ignore state_referenced_locally
	let initialZoom = zoom;
	let initialPinchCenter = { x: 0, y: 0 };
	// svelte-ignore state_referenced_locally
	let initPanXForPinch = panX;
	// svelte-ignore state_referenced_locally
	let initPanYForPinch = panY;
	let isPanning = false;
	let panStartX = 0;
	let panStartY = 0;
	let initPanX = 0;
	let initPanY = 0;

	// Momentum variables.
	let momentumVX = 0;
	let momentumVY = 0;
	let lastPanTime = 0;
	// svelte-ignore state_referenced_locally
	let lastPanX = panX;
	// svelte-ignore state_referenced_locally
	let lastPanY = panY;
	let momentumAnimationFrame = 0;
	let lastMomentumTime = 0;

	function getMidpoint(
		p1: { clientX: number; clientY: number },
		p2: { clientX: number; clientY: number },
	) {
		return {
			x: (p1.clientX + p2.clientX) / 2,
			y: (p1.clientY + p2.clientY) / 2,
		};
	}

	function getDistance(
		p1: { clientX: number; clientY: number },
		p2: { clientX: number; clientY: number },
	) {
		return Math.hypot(p1.clientX - p2.clientX, p1.clientY - p2.clientY);
	}

	function handlePointerDown(e: PointerEvent) {
		activePointers.set(e.pointerId, { clientX: e.clientX, clientY: e.clientY });
		const canvas = e.currentTarget as HTMLCanvasElement;
		canvas.setPointerCapture(e.pointerId);

		// Cancel any ongoing momentum.
		cancelAnimationFrame(momentumAnimationFrame);
		momentumVX = 0;
		momentumVY = 0;
		lastPanTime = performance.now();
		lastPanX = e.clientX;
		lastPanY = e.clientY;

		if (activePointers.size === 1) {
			isPanning = true;
			panStartX = e.clientX;
			panStartY = e.clientY;
			initPanX = panX;
			initPanY = panY;
			canvas.style.cursor = "grabbing";
		} else if (activePointers.size === 2) {
			isPinching = true;
			isPanning = false;
			const pointers = Array.from(activePointers.values());
			initialPinchDistance = getDistance(pointers[0], pointers[1]);
			initialZoom = zoom;
			initialPinchCenter = getMidpoint(pointers[0], pointers[1]);
			initPanXForPinch = panX;
			initPanYForPinch = panY;
		}
	}

	function handlePointerMove(e: PointerEvent) {
		if (!activePointers.has(e.pointerId)) return;
		activePointers.set(e.pointerId, { clientX: e.clientX, clientY: e.clientY });
		const canvas = e.currentTarget as HTMLCanvasElement;
		const now = performance.now();

		if (activePointers.size === 2) {
			const pointers = Array.from(activePointers.values());
			const currentDistance = getDistance(pointers[0], pointers[1]);
			const pinchRatio = currentDistance / initialPinchDistance;
			const newZoom = Math.max(0.1, initialZoom * pinchRatio);
			const currentMidpoint = getMidpoint(pointers[0], pointers[1]);
			const wx = (initialPinchCenter.x - initPanXForPinch) / initialZoom;
			const wy = (initialPinchCenter.y - initPanYForPinch) / initialZoom;
			panX = currentMidpoint.x - wx * newZoom;
			panY = currentMidpoint.y - wy * newZoom;
			zoom = newZoom;
		} else if (activePointers.size === 1 && isPanning) {
			// For panning, increase sensitivity on touch.
			const sensitivity = e.pointerType === "touch" ? 1.5 : 1;
			const dx = (e.clientX - panStartX) * sensitivity;
			const dy = (e.clientY - panStartY) * sensitivity;
			panX = initPanX + dx;
			panY = initPanY + dy;

			// Update momentum velocity.
			const dt = now - lastPanTime;
			if (dt > 0) {
				momentumVX = (e.clientX - lastPanX) / dt;
				momentumVY = (e.clientY - lastPanY) / dt;
			}
			lastPanTime = now;
			lastPanX = e.clientX;
			lastPanY = e.clientY;
		}
	}

	function handlePointerUp(e: PointerEvent) {
		activePointers.delete(e.pointerId);
		const canvas = e.currentTarget as HTMLCanvasElement;
		canvas.releasePointerCapture(e.pointerId);
		if (activePointers.size < 2) {
			isPinching = false;
			if (activePointers.size === 0) {
				isPanning = false;
				canvas.style.cursor = "grab";
				// Start momentum if velocity is significant.
				lastMomentumTime = performance.now();
				animateMomentum();
			} else {
				const remaining = activePointers.values().next().value;
				if (!remaining) return;
				isPanning = true;
				panStartX = remaining.clientX;
				panStartY = remaining.clientY;
				initPanX = panX;
				initPanY = panY;
			}
		}
	}

	function animateMomentum() {
		const now = performance.now();
		const dt = now - lastMomentumTime;
		lastMomentumTime = now;
		// Update pan position based on momentum.
		panX += momentumVX * dt;
		panY += momentumVY * dt;
		// Apply friction.
		momentumVX *= 0.95;
		momentumVY *= 0.95;
		drawCanvas(zoom, activeLevel);
		if (Math.abs(momentumVX) < 0.01 && Math.abs(momentumVY) < 0.01) return;
		momentumAnimationFrame = requestAnimationFrame(animateMomentum);
	}

	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		const canvas = e.currentTarget as HTMLCanvasElement;
		const rect = canvas.getBoundingClientRect();
		const pointerX = e.clientX - rect.left;
		const pointerY = e.clientY - rect.top;

		const oldZoom = zoom;
		const zoomFactor = 1 - e.deltaY * 0.001;
		const newZoom = Math.max(0.1, oldZoom * zoomFactor);

		const wx = (pointerX - panX) / oldZoom;
		const wy = (pointerY - panY) / oldZoom;
		panX = pointerX - wx * newZoom;
		panY = pointerY - wy * newZoom;
		zoom = newZoom;
	}

	// Attach event listeners and handle window resize.
	$effect(() => {
		const canvas = document.getElementById("canvas") as HTMLCanvasElement;
		if (!canvas) return;
		canvas.style.cursor = "grab";
		canvas.addEventListener("wheel", handleWheel, { passive: false });
		canvas.addEventListener("pointerdown", handlePointerDown);
		canvas.addEventListener("pointermove", handlePointerMove);
		canvas.addEventListener("pointerup", handlePointerUp);
		canvas.addEventListener("pointercancel", handlePointerUp);

		const handleResize = () => {
			canvasSize = { width: window.innerWidth - 100, height: window.innerHeight - 100 };
			imageScaledSize = {
				width: canvasSize.width,
				height: Math.floor(imageSize.height / (imageSize.width / canvasSize.width)),
			};
			drawCanvas(zoom, activeLevel);
		};
		window.addEventListener("resize", handleResize);

		return () => {
			canvas.removeEventListener("wheel", handleWheel);
			canvas.removeEventListener("pointerdown", handlePointerDown);
			canvas.removeEventListener("pointermove", handlePointerMove);
			canvas.removeEventListener("pointerup", handlePointerUp);
			canvas.removeEventListener("pointercancel", handlePointerUp);
			window.removeEventListener("resize", handleResize);
		};
	});
</script>

<main>
	<canvas id="canvas" width={canvasSize.width} height={canvasSize.height}></canvas>
</main>

<style>
	:global(body) {
		background-color: black;
		margin: 0;
		overflow: hidden;
	}
	/* Prevent default pinch-to-zoom on touch devices */
	canvas {
		touch-action: none;
	}
	main {
		display: flex;
		justify-content: center;
		align-items: center;
		width: 100vw;
		height: 100vh;
	}
</style>
