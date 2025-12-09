"""
Utility to clear both cache and database storage.
"""

import asyncio
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def clear_everything():
    """Clear both Redis cache and in-memory database"""
    
    print("🧹 Clearing all data...\n")
    
    # Import here to avoid issues
    try:
        from app.services import cache
        from app.services.repository import InMemoryRepository
        
        # Clear Redis cache
        if hasattr(cache, 'redis_client') and cache.redis_client:
            try:
                await cache.redis_client.flushdb()
                print("✅ Redis cache cleared")
            except Exception as e:
                print(f"⚠️  Redis clear failed: {e}")
        else:
            print("⚠️  Redis not connected (using in-memory cache)")
        
        # Clear in-memory cache if exists
        if hasattr(cache, '_cache_storage'):
            cache._cache_storage.clear()
            print("✅ In-memory cache cleared")
        
        # Clear in-memory database
        # The repository is likely instantiated elsewhere, so we need to access the global instance
        from app.services import repository as repo_module
        
        # Try to find the repository instance
        for attr_name in dir(repo_module):
            attr = getattr(repo_module, attr_name)
            if isinstance(attr, InMemoryRepository) and hasattr(attr, '_storage'):
                attr._storage.clear()
                print("✅ In-memory database cleared")
                break
        else:
            print("ℹ️  In-memory database not found or already empty")
        
        print("\n✨ All data cleared! Fresh scraping will happen on next request.\n")
        
    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        import traceback
        traceback.print_exc()

async def clear_specific_company(canonical_name: str):
    """Clear data for a specific company"""
    
    print(f"🧹 Clearing data for: {canonical_name}\n")
    
    try:
        from app.services import cache
        from app.services.repository import InMemoryRepository
        from app.services import repository as repo_module
        
        # Clear from Redis
        if hasattr(cache, 'redis_client') and cache.redis_client:
            try:
                key = f"company:{canonical_name}"
                deleted = await cache.redis_client.delete(key)
                if deleted:
                    print(f"✅ Cleared from Redis cache: {canonical_name}")
                else:
                    print(f"ℹ️  Not found in Redis cache: {canonical_name}")
            except Exception as e:
                print(f"⚠️  Redis clear failed: {e}")
        
        # Clear from in-memory cache
        if hasattr(cache, '_cache_storage'):
            cache_key = f"company:{canonical_name}"
            if cache_key in cache._cache_storage:
                del cache._cache_storage[cache_key]
                print(f"✅ Cleared from in-memory cache: {canonical_name}")
        
        # Clear from in-memory database
        for attr_name in dir(repo_module):
            attr = getattr(repo_module, attr_name)
            if isinstance(attr, InMemoryRepository) and hasattr(attr, '_storage'):
                if canonical_name in attr._storage:
                    del attr._storage[canonical_name]
                    print(f"✅ Cleared from database: {canonical_name}")
                else:
                    print(f"ℹ️  Not found in database: {canonical_name}")
                break
        
        print(f"\n✨ Data cleared for {canonical_name}! Fresh scraping will happen on next request.\n")
        
    except Exception as e:
        print(f"❌ Error clearing data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Clear specific company
        company = sys.argv[1].lower().strip()
        asyncio.run(clear_specific_company(company))
    else:
        # Clear everything
        asyncio.run(clear_everything())