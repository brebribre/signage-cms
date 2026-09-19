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


# --- HiveMQ MQTT client and its Netty transport -------------------------------------------
# Both reach their own classes by reflection (Netty picks transports and allocators by name),
# so R8 must keep them whole; the optional integrations they mention but we don't ship are
# not errors. From HiveMQ's own Android guide.
-keep class com.hivemq.client.** { *; }
-keep class io.netty.** { *; }
-keepclassmembers class io.netty.** { *; }
-dontwarn io.netty.**
# JCTools (Netty's lock-free queues) finds its own fields by name via reflection
# (consumerIndex, producerIndex …) — renamed, it throws NoSuchFieldException at start-up.
-keep class org.jctools.** { *; }
-keepclassmembers class org.jctools.** { *; }
-dontwarn org.jctools.**
-dontwarn reactor.blockhound.**
-dontwarn org.slf4j.**
-dontwarn org.apache.log4j.**
-dontwarn org.apache.logging.log4j.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.eclipse.jetty.**
-dontwarn com.google.protobuf.**
-dontwarn sun.security.**
-dontwarn javax.**
-dontwarn org.jboss.marshalling.**
-dontwarn com.aayushatharva.brotli4j.**
-dontwarn com.github.luben.zstd.**
-dontwarn com.jcraft.jzlib.**
-dontwarn com.ning.compress.**
-dontwarn lzma.sdk.**
-dontwarn net.jpountz.**
-dontwarn org.jetbrains.annotations.**

# --- kotlinx.serialization: every @Serializable model is looked up by its generated serializer
-keep,includedescriptorclasses class com.fortu.player.**$$serializer { *; }
-keepclassmembers class com.fortu.player.** {
    *** Companion;
}
-keepclasseswithmembers class com.fortu.player.** {
    kotlinx.serialization.KSerializer serializer(...);
}

# Stack traces stay readable in the debug overlay and the CMS error log.
-keepattributes SourceFile,LineNumberTable
