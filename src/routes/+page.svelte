<script lang="ts">
	const levels = 6;
	const imageSize = { width: 1600, height: 1486 };
	const canvasSize = { width: screen.width - 100, height: screen.height - 100 };
	// The full map dimensions at zoom 1.
	const imageScaledSize = {
		width: canvasSize.width,
		height: Math.floor(imageSize.height / (imageSize.width / canvasSize.width)),
	};

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

		if (src.includes("/0/0.")) {
			img.onload = () => {
				// Jank way to make the initial image render without user input
				zoom += 1;
				zoom -= 1;
			};
		}
		return img;
	}

	// Zoom state.
	let zoom = $state(1);
	// Pan offset: start centered.
	let panX = $state((canvasSize.width - imageScaledSize.width) / 2);
	let panY = $state((canvasSize.height - imageScaledSize.height) / 2);

	// activeLevel is the current level being rendered.
	let activeLevel = 0;
	// desiredLevel is computed from zoom.
	let desiredLevel = $derived(Math.min(levels - 1, Math.max(0, Math.floor(Math.log2(zoom)))));

	// When desiredLevel changes, record its timestamp.
	let desiredLevelTimestamp = Date.now();
	$effect(() => {
		// Track desiredLevel changes.
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
		// If nothing is visible, assume loaded.
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

		// Base tile boundaries.
		const baseX0 = col * tileWidth;
		const baseX1 = (col + 1) * tileWidth;
		const baseY0 = row * tileHeight;
		const baseY1 = (row + 1) * tileHeight;

		// Apply transform.
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

	// Draw the canvas with tiles from activeLevel, only drawing visible ones.
	function drawCanvas(z: number, level: number) {
		const canvas = document.getElementById("canvas") as HTMLCanvasElement;
		if (!canvas) return;
		canvas.width = canvasSize.width;
		canvas.height = canvasSize.height;
		const ctx = canvas.getContext("2d");
		if (!ctx) return;
		ctx.clearRect(0, 0, canvas.width, canvas.height);
		const indices = getVisibleTileIndices(level, z, panX, panY);
		indices.forEach((i) => {
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

	// Zoom on wheel events: zooming around the cursor.
	function handleWheel(e: WheelEvent) {
		e.preventDefault();
		const canvas = e.currentTarget as HTMLCanvasElement;
		const rect = canvas.getBoundingClientRect();
		const pointerX = e.clientX - rect.left;
		const pointerY = e.clientY - rect.top;

		const oldZoom = zoom;
		const zoomFactor = 1 - e.deltaY * 0.001; // Adjust sensitivity.
		const newZoom = Math.max(0.1, oldZoom * zoomFactor);

		// Compute world coordinates at the pointer.
		const wx = (pointerX - panX) / oldZoom;
		const wy = (pointerY - panY) / oldZoom;
		// Update pan so the pointer remains fixed.
		panX = pointerX - wx * newZoom;
		panY = pointerY - wy * newZoom;
		zoom = newZoom;
	}

	// Panning logic.
	let isPanning = false;
	let panStartX = 0;
	let panStartY = 0;
	let initPanX = 0;
	let initPanY = 0;
	function handlePointerDown(e: PointerEvent) {
		isPanning = true;
		panStartX = e.clientX;
		panStartY = e.clientY;
		initPanX = panX;
		initPanY = panY;
		(e.target as HTMLElement).style.cursor = "grabbing";
		(e.target as HTMLElement).setPointerCapture(e.pointerId);
	}
	function handlePointerMove(e: PointerEvent) {
		if (!isPanning) return;
		const dx = e.clientX - panStartX;
		const dy = e.clientY - panStartY;
		panX = initPanX + dx;
		panY = initPanY + dy;
	}
	function handlePointerUp(e: PointerEvent) {
		isPanning = false;
		(e.target as HTMLElement).style.cursor = "grab";
		(e.target as HTMLElement).releasePointerCapture(e.pointerId);
	}

	// Attach event listeners on mount.
	$effect(() => {
		const canvas = document.getElementById("canvas") as HTMLCanvasElement;
		if (!canvas) return;
		canvas.style.cursor = "grab";
		canvas.addEventListener("wheel", handleWheel, { passive: false });
		canvas.addEventListener("pointerdown", handlePointerDown);
		canvas.addEventListener("pointermove", handlePointerMove);
		canvas.addEventListener("pointerup", handlePointerUp);
		canvas.addEventListener("pointercancel", handlePointerUp);
		return () => {
			canvas.removeEventListener("wheel", handleWheel);
			canvas.removeEventListener("pointerdown", handlePointerDown);
			canvas.removeEventListener("pointermove", handlePointerMove);
			canvas.removeEventListener("pointerup", handlePointerUp);
			canvas.removeEventListener("pointercancel", handlePointerUp);
		};
	});
</script>

<main>
	<canvas id="canvas" width={canvasSize.width} height={canvasSize.height}></canvas>
</main>

<style>
	:global(body) {
		background-color: black;
	}

	main {
		display: flex;
		justify-content: center;
		align-items: center;
	}
</style>
