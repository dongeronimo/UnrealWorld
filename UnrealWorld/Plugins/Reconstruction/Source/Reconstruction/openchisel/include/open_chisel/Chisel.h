// The MIT License (MIT)
// Copyright (c) 2014 Matthew Klingensmith and Ivan Dryanovski
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

#ifndef CHISEL_H_
#define CHISEL_H_

#include <open_chisel/threading/Threading.h>
#include <open_chisel/ChunkManager.h>
#include <open_chisel/ProjectionIntegrator.h>
#include <open_chisel/geometry/Geometry.h>
#include <open_chisel/camera/PinholeCamera.h>
#include <open_chisel/camera/DepthImage.h>
#include <open_chisel/geometry/Frustum.h>
#include <open_chisel/pointcloud/PointCloud.h>

// LOCAL MODIFICATION: for the ray walk that replaced the frustum fill in
// IntegrateDepthScan.
#include <algorithm>
#include <cmath>
#include <unordered_map>

namespace chisel
{

    class Chisel
    {
        public:
            Chisel();
            Chisel(const Eigen::Vector3i& chunkSize, float voxelResolution, bool useColor);
            ~Chisel();

            inline const ChunkManager& GetChunkManager() const { return chunkManager; }

            /**
             * LOCAL: what the last IntegrateDepthScan actually did.
             *
             * Touched is not the same as GetChunks().size(), which is everything
             * ever allocated. This is the candidate set the ray walk produced on
             * the last frame, and it is the only sane denominator for the
             * integration timing: the same room costs five times more to
             * integrate looking down its length than at a wall an arm away, so a
             * millisecond figure on its own compares nothing.
             *
             * Discarded is how many of those were allocated, fully projected and
             * then handed straight back as empty. It is the number that says
             * whether the ray walk is working: under the old frustum fill it sat
             * near 90 percent of touched.
             * */
            inline size_t GetLastChunksTouched() const { return lastChunksTouched; }
            inline size_t GetLastChunksDiscarded() const { return lastChunksDiscarded; }
            inline float GetLastFrustumNear() const { return lastFrustumNear; }
            inline float GetLastFrustumFar() const { return lastFrustumFar; }
            inline ChunkManager& GetMutableChunkManager() { return chunkManager; }
            inline void SetChunkManager(const ChunkManager& manager) { chunkManager = manager; }

            void IntegratePointCloud(const ProjectionIntegrator& integrator,
                                     const PointCloud& cloud,
                                     const Transform& extrinsic,
                                     float maxDist);

            template <class DataType> void IntegrateDepthScan(const ProjectionIntegrator& integrator,
                                                              const std::shared_ptr<const DepthImage<DataType> >& depthImage,
                                                              const Transform& extrinsic,
                                                              const PinholeCamera& camera)
            {
                    DataType minimum, maximum, mean;
                    depthImage->GetStats(minimum, maximum, mean);

                    // LOCAL MODIFICATION: candidate chunks come from walking the
                    // observed RAYS, not from filling the frustum's volume.
                    //
                    // ## What was wrong with the frustum
                    //
                    // GetChunkIDsIntersecting(frustum) takes a solid cone from the
                    // nearest to the FURTHEST depth in the whole image, and hands
                    // back every chunk it crosses. Measured on device: 160 to 360
                    // chunks per frame, of which 88 to 94 percent were empty,
                    // allocated, fully projected (4096 voxels each) and then
                    // garbage collected. Two separate reasons, both of which this
                    // removes:
                    //
                    //  - the far plane is the max over the ENTIRE image, so the
                    //    cone runs to 2.4 m in every direction even where the real
                    //    surface is at 0.5 m. Everything beyond each direction's
                    //    own surface is visited for nothing;
                    //  - two thirds of ARCore's samples carry no depth estimate at
                    //    all. Those directions contribute no surface and no
                    //    carving, and the cone covers them anyway.
                    //
                    // Cost followed the cone's VOLUME, so it grew with the cube of
                    // whatever the sensor happened to see furthest that frame.
                    // Walking rays makes it follow the observed SURFACE instead,
                    // which is what lets the far plane grow without paying cubically
                    // for it.
                    //
                    // ## Why the walk starts at the camera and not at the band
                    //
                    // The obvious inversion collects only chunks within the
                    // truncation band around each surface point. That would be
                    // wrong here, and silently: ProjectionIntegrator carves on
                    // `surfaceDist > truncation + diag + carvingDist`, which is
                    // every voxel BETWEEN the camera and the surface, not a band
                    // around it. Skipping those chunks would switch carving off
                    // while leaving its config, its counters and its probe all in
                    // place, reporting success.
                    //
                    // So each ray is walked from the near plane to just past its
                    // own surface. That is the exact set of chunks this frame can
                    // affect, and no more.
                    const int depthWidth = depthImage->GetWidth();
                    const int depthHeight = depthImage->GetHeight();
                    const Intrinsics& intrinsics = camera.GetIntrinsics();
                    const float fx = intrinsics.GetFx();
                    const float fy = intrinsics.GetFy();
                    const float cx = intrinsics.GetCx();
                    const float cy = intrinsics.GetCy();

                    const Eigen::Vector3i chunkVoxels = chunkManager.GetChunkSize();
                    const float voxelResolution = chunkManager.GetResolution();
                    const float chunkExtent =
                            std::min(std::min(chunkVoxels.x(), chunkVoxels.y()), chunkVoxels.z()) *
                            voxelResolution;

                    // Half a chunk, so the walk cannot step over one. Sampling the
                    // segment more finely than this only repeats chunk IDs.
                    const float stepMetres = 0.5f * chunkExtent;

                    // Neighbouring pixels that land in the same chunk are the same
                    // ray as far as this is concerned. At the far plane a chunk
                    // spans chunkExtent metres, which is this many pixels; stepping
                    // by half of that cannot skip a chunk laterally either.
                    int pixelStride = 1;
                    if (maximum > 0.0f)
                    {
                        const float pixelsPerChunk = chunkExtent * fx / static_cast<float>(maximum);
                        pixelStride = std::max(1, static_cast<int>(0.5f * pixelsPerChunk));
                    }

                    // Reused across calls: this is per frame, and it would
                    // otherwise be an allocation and a free of a few hundred nodes
                    // sixty times a second.
                    candidateChunks.clear();
                    ChunkIDList chunksIntersecting;

                    for (int row = 0; row < depthHeight; row += pixelStride)
                    {
                        for (int col = 0; col < depthWidth; col += pixelStride)
                        {
                            const float depth =
                                    static_cast<float>(depthImage->DepthAt(row, col));
                            // NaN is ARCore's "no estimate here", which is most of
                            // the image. No ray, and that is the point.
                            if (std::isnan(depth) || depth <= 0.0f)
                            {
                                continue;
                            }

                            // Pixel to a unit ray in camera space. Chisel's camera
                            // space has +Z forward, which is what the extrinsic's
                            // Y/Z flip already arranged for.
                            const Vec3 direction((static_cast<float>(col) - cx) / fx,
                                                 (static_cast<float>(row) - cy) / fy,
                                                 1.0f);

                            // Past the surface by a truncation, so the far side of
                            // the band is included. The near end is the frustum's
                            // near plane rather than zero: closer than that is
                            // inside the phone.
                            const float truncation =
                                    integrator.GetTruncator().GetTruncationDistance(depth);
                            const float rayEnd = depth + truncation + chunkExtent;
                            const float rayStart = std::max(static_cast<float>(minimum), stepMetres);

                            // Where the band begins. Inside it a chunk may be
                            // CREATED, because that is where new surface appears.
                            // Outside it, nearer the camera, the only thing that
                            // can happen is carving, and carving an unallocated
                            // chunk has nothing to remove: creating one there
                            // costs an allocation and 4096 projections to
                            // discover it is still empty, which was the whole
                            // remaining waste after the ray walk landed.
                            const float bandBegins = depth - truncation - chunkExtent;

                            for (float t = rayStart; t <= rayEnd; t += stepMetres)
                            {
                                const Vec3 pointInCamera = direction * t;
                                const Vec3 point = extrinsic * pointInCamera;
                                const ChunkID id = chunkManager.GetIDAt(point);
                                const bool mayAllocate = t >= bandBegins;

                                const auto inserted = candidateChunks.insert({id, mayAllocate});
                                if (inserted.second)
                                {
                                    chunksIntersecting.push_back(id);
                                }
                                else if (mayAllocate)
                                {
                                    // A chunk reached by two rays, one of which
                                    // has its surface here. Permission is the
                                    // union: any ray that wants to build in it
                                    // is enough.
                                    inserted.first->second = true;
                                }
                            }
                        }
                    }

                    // LOCAL: the numbers that actually drive this call's cost,
                    // recorded for the probe in Reconstruction.
                    //
                    // Integration is per VOXEL of every chunk this visits, so
                    // `chunks touched` is the quantity to watch, and it is not the
                    // same as the chunk count the map holds. Near and far are the
                    // depth image's own min and max, kept because they are what the
                    // old frustum was built from and so the thing to compare
                    // against when reading the count.
                    lastChunksTouched = chunksIntersecting.size();
                    lastFrustumNear = static_cast<float>(minimum);
                    lastFrustumFar = static_cast<float>(maximum);

                    std::mutex mutex;
                    ChunkIDList garbageChunks;
                    for(const ChunkID& chunkID : chunksIntersecting)
                    //parallel_for(chunksIntersecting.begin(), chunksIntersecting.end(), [&](const ChunkID& chunkID)
                    {
                        bool chunkNew = false;

                        mutex.lock();
                        if (!chunkManager.HasChunk(chunkID))
                        {
                           // LOCAL MODIFICATION: only the band may build.
                           //
                           // A chunk that does not exist and was reached only by
                           // the carving stretch of some ray has nothing in it to
                           // carve. Creating it here would cost the allocation
                           // plus a full 4096-voxel pass to establish that it is
                           // still empty, followed by garbage collection. That
                           // was the entire remainder of the waste the ray walk
                           // did not already remove, 18 to 24 percent of it.
                           //
                           // No correctness change: chunks that already exist are
                           // integrated as before no matter which stretch of which
                           // ray reached them, because carving those is the point.
                           if (!candidateChunks[chunkID])
                           {
                               mutex.unlock();
                               continue;
                           }
                           chunkNew = true;
                           chunkManager.CreateChunk(chunkID);
                        }

                        ChunkPtr chunk = chunkManager.GetChunk(chunkID);
                        mutex.unlock();

                        bool needsUpdate = integrator.Integrate(depthImage, camera, extrinsic, chunk.get());

                        mutex.lock();
                        if (needsUpdate)
                        {
                            for (int dx = -1; dx <= 1; dx++)
                            {
                                for (int dy = -1; dy <= 1; dy++)
                                {
                                    for (int dz = -1; dz <= 1; dz++)
                                    {
                                        meshesToUpdate[chunkID + ChunkID(dx, dy, dz)] = true;
                                    }
                                }
                            }
                        }
                        else if(chunkNew)
                        {
                            garbageChunks.push_back(chunkID);
                        }
                        mutex.unlock();
                    }
                    //);
                    // LOCAL: chunks this frame reached that held nothing and are
                    // being handed straight back. Every one of them was allocated
                    // and had all of its voxels projected before being discarded,
                    // so this share of `touched` is wasted work, and it is the
                    // number that says whether the ray walk and the creation gate
                    // above are doing what they claim: it has to fall from ~90
                    // percent to ~20.
                    lastChunksDiscarded = garbageChunks.size();
                    GarbageCollect(garbageChunks);
                    //chunkManager.PrintMemoryStatistics();
            }

            template <class DataType, class ColorType> void IntegrateDepthScanColor(const ProjectionIntegrator& integrator, const std::shared_ptr<const DepthImage<DataType> >& depthImage,  const Transform& depthExtrinsic, const PinholeCamera& depthCamera, const std::shared_ptr<const ColorImage<ColorType> >& colorImage, const Transform& colorExtrinsic, const PinholeCamera& colorCamera)
            {
                    Frustum frustum;
                    depthCamera.SetupFrustum(depthExtrinsic, &frustum);

                    ChunkIDList chunksIntersecting;
                    chunkManager.GetChunkIDsIntersecting(frustum, &chunksIntersecting);

                    std::mutex mutex;
                    ChunkIDList garbageChunks;
                    //for ( const ChunkID& chunkID : chunksIntersecting)
                    parallel_for(chunksIntersecting.begin(), chunksIntersecting.end(), [&](const ChunkID& chunkID)
                    {

                        mutex.lock();
                        bool chunkNew = false;
                        if (!chunkManager.HasChunk(chunkID))
                        {
                           chunkNew = true;
                           chunkManager.CreateChunk(chunkID);
                        }

                        ChunkPtr chunk = chunkManager.GetChunk(chunkID);
                        mutex.unlock();


                        bool needsUpdate = integrator.IntegrateColor(depthImage, depthCamera, depthExtrinsic, colorImage, colorCamera, colorExtrinsic, chunk.get());

                        mutex.lock();
                        if (needsUpdate)
                        {
                            for (int dx = -1; dx <= 1; dx++)
                            {
                                for (int dy = -1; dy <= 1; dy++)
                                {
                                    for (int dz = -1; dz <= 1; dz++)
                                    {
                                        meshesToUpdate[chunkID + ChunkID(dx, dy, dz)] = true;
                                    }
                                }
                            }
                        }
                        else if(chunkNew)
                        {
                            garbageChunks.push_back(chunkID);
                        }
                        mutex.unlock();
                    }
                    );

                    GarbageCollect(garbageChunks);
                    //chunkManager.PrintMemoryStatistics();
            }

            void GarbageCollect(const ChunkIDList& chunks);
            void UpdateMeshes();

            bool SaveAllMeshesToPLY(const std::string& filename);
            void Reset();

            const ChunkSet& GetMeshesToUpdate() const { return meshesToUpdate; }

            // LOCAL MODIFICATION: mutable access to the dirty set.
            //
            // Upstream's only way to remesh is UpdateMeshes(), which does EVERY
            // dirty chunk and then clears the set. Sweeping a room dirties
            // hundreds at once -- integration marks the whole 3x3x3 neighbourhood
            // of every touched chunk, a few lines above -- and marching cubes on
            // all of them inside one frame is a dropped frame.
            //
            // With this, a caller can take a bounded number per frame and leave
            // the rest marked, which is what putorana::recon::Reconstruction does.
            ChunkSet& GetMutableMeshesToUpdate() { return meshesToUpdate; }

        protected:
            ChunkManager chunkManager;
            ChunkSet meshesToUpdate;

            // LOCAL MODIFICATION: the ray walk's dedup set, a member purely so
            // its buckets survive between frames. Rebuilding it sixty times a
            // second is a few hundred allocations that buy nothing.
            // The value is whether that chunk may be CREATED: true when some ray
            // put its truncation band there, false when every ray that reached it
            // was only passing through on its way to a surface further out.
            std::unordered_map<ChunkID, bool, ChunkHasher> candidateChunks;

            /** LOCAL: see the getters above. Written by IntegrateDepthScan. */
            size_t lastChunksTouched = 0;
            size_t lastChunksDiscarded = 0;
            float lastFrustumNear = 0.0f;
            float lastFrustumFar = 0.0f;

    };
    typedef std::shared_ptr<Chisel> ChiselPtr;
    typedef std::shared_ptr<const Chisel> ChiselConstPtr;

} // namespace chisel 

#endif // CHISEL_H_ 
