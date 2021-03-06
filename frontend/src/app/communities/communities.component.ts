import { Component, OnInit } from '@angular/core';
import { Community } from '../community';
import { CommunityService } from '../community.service';
import { MessageService } from '../message.service';
import {LoadingAnimationService} from '../loading-animation.service';

declare var communitiesBox: any;
declare var communitiesComponent: any;


@Component({
    selector: 'app-communities',
    templateUrl: './communities.component.html',
    styleUrls: ['./communities.component.css']
})
export class CommunitiesComponent implements OnInit {
    communities: Community[] = [];
    timers: any[] = [];
    subscriptions: any[] = [];
    count_subscription: any;
    page = 0;
    count: any = 0;

    private searchParams: any = {};

    constructor(
        private communitiesService: CommunityService,
        private messageService: MessageService,
        private loadingAnimationService: LoadingAnimationService,
    ) {}

    ngOnInit() {
    }

    searchParametersChanged(searchParameters: any): void {
        this.searchParams = searchParameters;

        this.resetTape();
        this.loadMore();

        this.count = '-';
        if (this.count_subscription) {
          this.count_subscription.unsubscribe();
        }
        this.count_subscription = this.communitiesService.count(this.searchParams, 0).subscribe(result => {
            this.count = result.count;
        });
    }

    loadMore() {
        this.loadingAnimationService.start();
        this.subscriptions.push(this.communitiesService.search(
                    this.searchParams, this.page
            ).subscribe(result => {
                this.loadingAnimationService.stop();
                ++this.page;
                if (!result.data.length) {
                    return;
                }

                for (const community of result.data) {
                    this.communities.push(new Community(community));
                }

                /*if (!result.next) {
                    this.messageService.info("Больше ничего нет");
                    return;
                }*/

                if (communitiesBox.scrollHeight < communitiesComponent.scrollHeight + 500) {
                    this.timers.push(setTimeout(() => this.loadMore(), 100));
                }
            })
        );
    }

    resetTape() {
        this.communities = [];
        for (const timer of this.timers) {
          clearTimeout(timer);
        }

        for (const subscription of this.subscriptions) {
            subscription.unsubscribe();
            this.loadingAnimationService.stop();
        }

        this.subscriptions = [];
        this.timers = [];
        this.page = 0;
    }

    onScroll() {
        this.loadMore();
    }

    public sortByFields: any[] = [
        {
            fieldName: 'subscribers_count',
            humanReadableName: {
                sortBy: 'Количеству подписчиков',
                name: 'подписчиков',
            }
        },
        {
            fieldName: 'stories_count',
            humanReadableName: {
                sortBy: 'Количеству постов',
                name: 'постов',
            }
        },
        {
            fieldName: 'last_update_timestamp',
            humanReadableName: {
                sortBy: 'Времени последнего обновления',
                name: 'Время последнего обновления',
            }
        },
        {
            fieldName: 'name',
            humanReadableName: {
                sortBy: 'Названию',
                name: '',
            }
        },
    ];
}
