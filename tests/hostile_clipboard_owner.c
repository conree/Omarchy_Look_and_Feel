#define _GNU_SOURCE
#include <wayland-client.h>
#include "data-control.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <pthread.h>
#include <stdint.h>
#include <time.h>
static struct zwlr_data_control_manager_v1 *manager;
static struct wl_seat *seat;
static int burst;
static void *stream(void *arg) {
 int fd=(int)(intptr_t)arg; char buf[65536]; memset(buf,'x',sizeof buf);
 size_t total=0, n=burst?sizeof buf:4096; struct timespec delay={0,burst?1000000:50000000};
 for(int i=0;i<(burst?2048:240);i++) {
   ssize_t sent=write(fd,buf,n); if(sent<=0) break; total+=sent; nanosleep(&delay,NULL);
 }
 fprintf(stderr,"STREAM_END bytes=%zu\n",total); fflush(stderr); close(fd); return NULL;
}
static void send_data(void *data, struct zwlr_data_control_source_v1 *source,const char *mime,int32_t fd) {
 fprintf(stderr,"SEND_REQUEST mime=%s\n",mime); fflush(stderr);
 pthread_t t; pthread_create(&t,NULL,stream,(void*)(intptr_t)fd); pthread_detach(t);
}
static void cancelled(void *data,struct zwlr_data_control_source_v1 *s) { fprintf(stderr,"CANCELLED\n"); fflush(stderr); }
static const struct zwlr_data_control_source_v1_listener source_listener={send_data,cancelled};
static void global(void *data,struct wl_registry *registry,uint32_t name,const char *interface,uint32_t version) {
 if(!strcmp(interface,"zwlr_data_control_manager_v1")) manager=wl_registry_bind(registry,name,&zwlr_data_control_manager_v1_interface,version<2?version:2);
 if(!strcmp(interface,"wl_seat")) seat=wl_registry_bind(registry,name,&wl_seat_interface,1);
}
static void removed(void *data,struct wl_registry *registry,uint32_t name) {}
static const struct wl_registry_listener registry_listener={global,removed};
static void offer_mime(void *d,struct zwlr_data_control_offer_v1 *o,const char *mime) {}
static const struct zwlr_data_control_offer_v1_listener offer_listener={offer_mime};
static void data_offer(void *d,struct zwlr_data_control_device_v1 *dev,struct zwlr_data_control_offer_v1 *o) {zwlr_data_control_offer_v1_add_listener(o,&offer_listener,NULL);}
static void selection(void *d,struct zwlr_data_control_device_v1 *dev,struct zwlr_data_control_offer_v1 *o) {}
static void finished(void *d,struct zwlr_data_control_device_v1 *dev) {}
static const struct zwlr_data_control_device_v1_listener device_listener={data_offer,selection,finished,selection};
int main(int argc,char **argv) {
 signal(SIGPIPE,SIG_IGN); burst=argc>1 && !strcmp(argv[1],"burst");
 struct wl_display *display=wl_display_connect(NULL); if(!display) return 2;
 struct wl_registry *registry=wl_display_get_registry(display); wl_registry_add_listener(registry,&registry_listener,NULL); wl_display_roundtrip(display);
 if(!manager || !seat) {fprintf(stderr,"Missing data-control manager or seat\n");return 3;}
 struct zwlr_data_control_source_v1 *source=zwlr_data_control_manager_v1_create_data_source(manager);
 zwlr_data_control_source_v1_add_listener(source,&source_listener,NULL);
 zwlr_data_control_source_v1_offer(source,"text/plain;charset=utf-8");
 zwlr_data_control_source_v1_offer(source,"text/plain");
 struct zwlr_data_control_device_v1 *device=zwlr_data_control_manager_v1_get_data_device(manager,seat);
 zwlr_data_control_device_v1_add_listener(device,&device_listener,NULL);
 zwlr_data_control_device_v1_set_selection(device,source);
 wl_display_flush(display); fprintf(stderr,"OFFER_READY mode=%s\n",burst?"burst":"slow");fflush(stderr);
 while(wl_display_dispatch(display)!=-1) {} return 0;
}
