# kotlinx.serialization keeps its generated serializers via annotations; without this a
# minified release build fails to deserialize the manifest at runtime rather than at compile
# time, which is the worst place to find out.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.**
-keepclassmembers class com.fortu.player.api.** {
    *** Companion;
}
-keepclasseswithmembers class com.fortu.player.api.** {
    kotlinx.serialization.KSerializer serializer(...);
}
